import time
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models.schemas import AcousticFeatures, DeepfakeDetectionResult
from app.services.audio.preprocessing import load_audio_resampled, validate_speech_activity


class BaseDeepfakeDetector(ABC):
    @abstractmethod
    def detect(self, audio_path: Path | None, features: AcousticFeatures) -> DeepfakeDetectionResult | None:
        pass


class PretrainedAntiSpoofAdapter(BaseDeepfakeDetector):
    """
    Adapter for Hugging Face pretrained anti-spoofing and synthetic speech classification models.
    Operates on 16kHz mono audio on CPU or GPU.
    """

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._classifier = None
        self._model_loaded = False
        self._model_error = None

    def detect(self, audio_path: Path | None, features: AcousticFeatures) -> DeepfakeDetectionResult | None:
        if not audio_path or not audio_path.exists():
            return None

        # Load resampled 16kHz audio array for standardized model inference
        audio_arr, sample_rate = load_audio_resampled(audio_path, target_sr=16000)

        # Explicit Audio Validation Gate: Do not pass silence/micro-noise to neural classifier
        is_speech, reason, _ = validate_speech_activity(audio_arr, sample_rate)
        if not is_speech:
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.model_id,
                model_type="pretrained_antispoofing",
                model_status="skipped",
                model_inference_skipped=True,
                skip_reason="insufficient_speech_audio",
                inference_time_ms=0.0,
                fallback_used=False,
                reasons=[f"Model inference skipped: {reason}"],
            )

        start_time = time.perf_counter()
        try:
            classifier = self._get_classifier()
            if not self._model_loaded or classifier is None:
                return None

            # Predict using pipeline
            if hasattr(audio_arr, "tolist"):
                input_data = {"raw": audio_arr, "sampling_rate": sample_rate}
            else:
                input_data = str(audio_path)

            predictions: list[dict[str, Any]] = classifier(input_data)
            inference_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result = self._parse_predictions(predictions, inference_ms)
            if result:
                result.model_type = "pretrained_antispoofing"
                result.model_status = "loaded"
            return result

        except Exception as exc:
            self._model_error = str(exc)
            return None

    def _get_classifier(self):
        if self._classifier is None:
            self._classifier, self._model_loaded = _load_transformers_pipeline(self.model_id)
        return self._classifier

    def _parse_predictions(self, predictions: list[dict[str, Any]], inference_ms: float) -> DeepfakeDetectionResult:
        synthetic_score = 0.0
        real_score = 0.0
        best_label = "unknown"
        reasons = []

        for item in predictions:
            label = str(item.get("label", "")).lower()
            score = float(item.get("score", 0.0))

            if any(token in label for token in ("fake", "spoof", "synthetic", "clone", "generated", "deepfake", "ai")):
                synthetic_score = max(synthetic_score, score)
                best_label = label
            elif any(token in label for token in ("bonafide", "genuine", "real", "human", "natural", "live")):
                real_score = max(real_score, score)
                best_label = label

        if synthetic_score == 0.0 and real_score == 0.0:
            return DeepfakeDetectionResult(
                prediction="REAL",
                synthetic_probability=0.08,
                real_probability=0.92,
                model_name=self.model_id,
                model_type="pretrained_antispoofing",
                model_status="loaded",
                inference_time_ms=inference_ms,
                fallback_used=False,
                reasons=["Model provided inconclusive classification. Defaulted to conservative baseline."],
            )

        total = synthetic_score + real_score
        if total > 0:
            synthetic_prob = synthetic_score / total
            real_prob = real_score / total
        else:
            synthetic_prob = synthetic_score
            real_prob = 1.0 - synthetic_score

        prediction = "SYNTHETIC" if synthetic_prob >= 0.50 else "REAL"
        confidence_pct = round(max(synthetic_prob, real_prob) * 100, 1)

        if synthetic_prob >= 0.75:
            reasons.append(f"Pretrained anti-spoofing model ({self.model_id}) detected synthetic voice artifacts with {confidence_pct}% confidence (label: '{best_label}').")
        else:
            reasons.append(f"Pretrained anti-spoofing model ({self.model_id}) classified voice as {prediction} ({confidence_pct}% confidence).")

        return DeepfakeDetectionResult(
            prediction=prediction,
            synthetic_probability=round(min(max(synthetic_prob, 0.01), 0.99), 3),
            real_probability=round(min(max(real_prob, 0.01), 0.99), 3),
            model_name=self.model_id,
            model_type="pretrained_antispoofing",
            model_status="loaded",
            inference_time_ms=inference_ms,
            fallback_used=False,
            reasons=reasons,
        )


class ExplainableAcousticDetector(BaseDeepfakeDetector):
    """
    Multi-Signal Acoustic Forensic Engine.
    Analyzes physical voice production cues: pitch (F0) trajectory, pitch standard deviation/jitter,
    dynamic intensity envelope, spectral formant contrast, spectral flatness, and zero-crossing dynamics.

    Produces three calibrated states:
    - Likely Human (LIKELY_HUMAN)
    - Suspicious / Uncertain (INCONCLUSIVE / POSSIBLE_SYNTHETIC)
    - Likely AI-Generated / Cloned (HIGH_CONFIDENCE_SYNTHETIC / POSSIBLE_SYNTHETIC)
    """

    MODEL_NAME = "VoiceShield-Acoustic-v2"

    def detect(self, audio_path: Path | None, features: AcousticFeatures) -> DeepfakeDetectionResult:
        # Explicit Silence / Insufficient Energy Check
        if features.rms_energy < 0.0030 or features.dynamic_range < 0.015:
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.MODEL_NAME,
                model_type="acoustic_forensic_engine",
                model_status="skipped",
                model_inference_skipped=True,
                skip_reason="insufficient_speech_audio",
                inference_time_ms=0.0,
                fallback_used=True,
                reasons=["Acoustic inspection skipped: insufficient voice energy."],
            )

        start_time = time.perf_counter()
        reasons: list[str] = []

        # Load resampled audio array for frame-by-frame forensic analysis if path is available
        samples_arr = None
        sr = 16000
        if audio_path and Path(audio_path).exists():
            try:
                samples_arr, sr = load_audio_resampled(Path(audio_path), target_sr=16000)
            except Exception:
                samples_arr = None

        duration = features.duration_seconds or 0.0
        synthetic_score = 0.10  # Baseline neutral prior

        if samples_arr is not None and len(samples_arr) > int(0.25 * sr):
            import numpy as np

            arr = samples_arr if isinstance(samples_arr, np.ndarray) else np.array(samples_arr, dtype=np.float32)
            frame_len = int(0.025 * sr)
            frame_step = int(0.010 * sr)
            num_frames = (len(arr) - frame_len) // frame_step

            frame_energies = []
            frame_pitches = []
            frame_zcr = []
            spectral_flatness_list = []
            frame_contrasts = []

            for i in range(max(0, num_frames)):
                frame = arr[i * frame_step : i * frame_step + frame_len]
                f_rms = float(np.sqrt(np.mean(frame**2)))
                frame_energies.append(f_rms)

                diff_signs = np.diff(np.signbit(frame))
                frame_zcr.append(float(np.mean(diff_signs)))

                if len(frame) >= 256 and f_rms > 0.008:
                    fft_mag = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
                    power = fft_mag ** 2
                    gmean = float(np.exp(np.mean(np.log(power + 1e-12))))
                    amean = float(np.mean(power) + 1e-12)
                    spectral_flatness_list.append(gmean / amean)

                    if np.max(fft_mag) > 1e-6:
                        norm_fft = fft_mag / np.max(fft_mag)
                        peak_sub = float(np.max(norm_fft[: len(norm_fft) // 2]))
                        valley_sub = float(np.mean(norm_fft[len(norm_fft) // 2 :]))
                        frame_contrasts.append(peak_sub - valley_sub)

                # Autocorrelation Pitch Estimation (70Hz - 400Hz)
                if f_rms > 0.008:
                    corr = np.correlate(frame, frame, mode="full")
                    corr = corr[len(corr) // 2 :]
                    min_lag = int(sr / 400)
                    max_lag = int(sr / 70)
                    if max_lag < len(corr):
                        peak_lag = min_lag + int(np.argmax(corr[min_lag:max_lag]))
                        if corr[peak_lag] > 0.30 * corr[0]:
                            frame_pitches.append(sr / float(peak_lag))

            pitch_count = len(frame_pitches)
            pitch_std = float(np.std(frame_pitches)) if pitch_count >= 5 else 0.0
            pitch_mean = float(np.mean(frame_pitches)) if pitch_count >= 5 else 0.0

            # Pitch Jitter
            if pitch_count >= 8:
                pitch_diffs = np.abs(np.diff(frame_pitches))
                pitch_jitter = float(np.mean(pitch_diffs))
            else:
                pitch_jitter = 0.0

            rms = float(np.sqrt(np.mean(arr**2)))
            energy_std = float(np.std(frame_energies)) if frame_energies else 0.0
            energy_cv = energy_std / (rms + 1e-6)
            dyn_range = float(np.max(arr) - np.min(arr)) if len(arr) > 0 else 0.0
            mean_flatness = float(np.mean(spectral_flatness_list)) if spectral_flatness_list else 0.0

            # 1. Fundamental Frequency & Prosodic Pitch Dynamics
            if pitch_count >= 8:
                if pitch_std < 5.0:
                    synthetic_score += 0.50
                    reasons.append(f"Abnormally flat robotic pitch contour detected (pitch variation: {pitch_std:.1f}Hz, biological speech threshold: >=15Hz).")
                elif pitch_std < 12.0:
                    synthetic_score += 0.25
                    reasons.append(f"Constrained vocal prosody with reduced natural pitch inflection ({pitch_std:.1f}Hz std).")
                elif pitch_std >= 22.0:
                    synthetic_score -= 0.15
                    reasons.append(f"Natural biological pitch inflection observed ({pitch_std:.1f}Hz standard deviation across syllables).")

                if pitch_jitter > 50.0:
                    synthetic_score += 0.20
                    reasons.append(f"Elevated pitch discontinuity / vocoder phase jump detected ({pitch_jitter:.1f}Hz jitter).")
            else:
                reasons.append("Limited voiced pitch frames detected for trajectory evaluation.")

            # 2. Dynamic Energy Envelope & Syllabic Modulation
            if energy_cv < 0.10 and duration >= 1.5:
                synthetic_score += 0.35
                reasons.append("Unnaturally flat dynamic energy envelope with absence of biological syllabic decay.")
            elif energy_cv > 0.35:
                synthetic_score -= 0.10
                reasons.append("Dynamic syllabic modulation matches natural biological speech breathing and articulation.")

            # 3. Dynamic Range & Contrast
            if dyn_range < 0.20 and rms > 0.01:
                synthetic_score += 0.20
                reasons.append("Severely compressed dynamic range characteristic of synthesized carrier signals.")
            elif features.spectral_contrast < 0.005:
                synthetic_score += 0.25
                reasons.append("Spectral contrast collapse characteristic of vocoded acoustic carriers.")

            # 4. Spectral Flatness & Phase Noise
            if mean_flatness > 0.15:
                synthetic_score += 0.20
                reasons.append("Elevated spectral flatness indicative of synthetic vocoder noise injection.")

        else:
            # Fallback using precomputed summary AcousticFeatures
            if features.spectral_contrast < 0.005:
                synthetic_score += 0.35
                reasons.append("Severe spectral contrast collapse characteristic of synthetic carrier signals.")
            if features.dynamic_range < 0.15 and features.rms_energy > 0.01:
                synthetic_score += 0.30
                reasons.append("Severely compressed dynamic range indicating artificial audio generation.")
            if features.zero_crossing_rate > 0.35 and features.byte_entropy > 0.95:
                synthetic_score += 0.25
                reasons.append("Elevated zero-crossing density and phase noise exceeding standard vocal tract characteristics.")

        synthetic_prob = round(max(0.02, min(0.98, synthetic_score)), 3)
        real_prob = round(1.0 - synthetic_prob, 3)

        # 3-State Calibrated Prediction Mapping
        if duration < 2.0:
            prediction = "INCONCLUSIVE"
            reasons.append("Recording duration is short (<2.0s); voice authenticity is classified as Suspicious / Inconclusive.")
        elif synthetic_prob >= 0.65:
            prediction = "SYNTHETIC"
        elif synthetic_prob >= 0.35:
            prediction = "INCONCLUSIVE"
            reasons.append("Acoustic parameters exhibit ambiguous characteristics between natural and synthesized audio.")
        else:
            prediction = "REAL"
            reasons.append("Acoustic voice production cues are consistent with biological human vocal tract dynamics.")

        inference_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DeepfakeDetectionResult(
            prediction=prediction,
            synthetic_probability=synthetic_prob,
            real_probability=real_prob,
            model_name=self.MODEL_NAME,
            model_type="acoustic_forensic_engine",
            model_status="loaded",
            inference_time_ms=inference_ms,
            fallback_used=True,
            reasons=reasons,
        )


@lru_cache(maxsize=1)
def _load_transformers_pipeline(model_id: str):
    try:
        from transformers import pipeline, AutoModelForAudioClassification, AutoFeatureExtractor

        BLOCKED_GENERIC_MODELS = [
            "facebook/wav2vec2-base",
            "facebook/wav2vec2-large",
            "facebook/wav2vec2-base-960h",
            "facebook/wav2vec2-large-960h",
            "microsoft/wavlm-base",
            "microsoft/wavlm-large",
            "microsoft/wavlm-base-plus",
            "facebook/hubert-base-ls960",
            "facebook/hubert-large-ls960-ft",
        ]
        BLOCKED_KEYWORDS = [
            "wavlm-base-plus-sv",
        ]

        if model_id in BLOCKED_GENERIC_MODELS or any(kw in model_id for kw in BLOCKED_KEYWORDS):
            print(f"[WARNING] {model_id} is not an anti-spoofing classifier.")
            return None, False

        # Attempt to load with local_files_only to avoid hanging/blocking on network requests
        try:
            model = AutoModelForAudioClassification.from_pretrained(model_id, local_files_only=True)
            feature_extractor = AutoFeatureExtractor.from_pretrained(model_id, local_files_only=True)
            classifier = pipeline("audio-classification", model=model, feature_extractor=feature_extractor, device="cpu")
            print(f"[SUCCESS] Loaded cached anti-spoofing model: {model_id}")
            return classifier, True
        except Exception:
            print(f"[INFO] Pretrained model {model_id} not cached locally. Running with Acoustic Baseline.")
            return None, False
    except Exception as exc:
        print(f"[INFO] Neural anti-spoofing pipeline unavailable: {exc}. Using Acoustic Baseline.")
        return None, False



def detect_synthetic_voice_detailed(features: AcousticFeatures, audio_path: Path | None = None) -> DeepfakeDetectionResult:
    settings = get_settings()

    if settings.deepfake_model_id and audio_path:
        adapter = PretrainedAntiSpoofAdapter(settings.deepfake_model_id)
        res = adapter.detect(audio_path, features)
        if res is not None and res.model_type == "pretrained_antispoofing":
            return res

    fallback_detector = ExplainableAcousticDetector()
    result = fallback_detector.detect(audio_path, features)
    return result


def detect_synthetic_voice(features: AcousticFeatures, audio_path: Path | None = None) -> tuple[float, list[str]]:
    result = detect_synthetic_voice_detailed(features, audio_path)
    return result.synthetic_probability, result.reasons

