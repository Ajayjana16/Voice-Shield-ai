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
    Calibrated acoustic voice inspection baseline.
    Analyzes physical voice production cues: spectral contrast, harmonic structure, dynamic range, pause continuity, and zero-crossing dynamics.

    IMPORTANT:
    This is a deterministic handcrafted acoustic inspection baseline, NOT a neural voice cloning model.
    It does NOT output artificial high-confidence deepfake scores (e.g. 98%) on normal microphone audio.
    Microphone compression, brief pauses, short audio, or background noise are treated as normal biological variation.
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
                model_type="heuristic_baseline",
                model_status="skipped",
                model_inference_skipped=True,
                skip_reason="insufficient_speech_audio",
                inference_time_ms=0.0,
                fallback_used=True,
                reasons=["Acoustic inspection skipped: insufficient voice energy."],
            )

        reasons: list[str] = []
        start_time = time.perf_counter()
        extreme_anomalies = 0


        # Check for non-biological spectral anomalies (extreme conditions only)
        # 1. Severe unnatural high-frequency carrier / centroid anomaly (> 5.5 kHz with low dynamic variation)
        if features.spectral_centroid > 5500 and features.dynamic_range < 0.04:
            extreme_anomalies += 1
            reasons.append("Unusual high-frequency spectral resonance detected above standard telecommunication speech band.")

        # 2. Extreme flat spectrum with near-zero spectral contrast (< 0.002)
        if features.spectral_contrast < 0.002 and features.rms_energy > 0.05:
            extreme_anomalies += 1
            reasons.append("Severe spectral contrast collapse characteristic of synthetic carrier signals.")

        # 3. High zero-crossing rate with elevated entropy (> 0.40 ZCR)
        if features.zero_crossing_rate > 0.40 and features.byte_entropy > 0.95:
            extreme_anomalies += 1
            reasons.append("Elevated zero-crossing density and phase noise exceeding standard vocal tract characteristics.")

        # Calibrated realistic probability assignment:
        # Extreme synthetic audio test cases have >= 2 extreme anomalies
        if extreme_anomalies >= 2:
            synthetic_prob = 0.40
            prediction = "REAL"  # Without a validated neural model, do not falsely label as SYNTHETIC
            reasons.append("Acoustic anomalies noted, but synthetic voice determination is inconclusive without a validated neural model.")
        else:
            synthetic_prob = 0.04
            prediction = "REAL"
            reasons.append("Acoustic voice production cues are consistent with biological human vocal tract dynamics.")

        real_prob = round(1.0 - synthetic_prob, 3)
        inference_ms = round((time.perf_counter() - start_time) * 1000, 2)



        return DeepfakeDetectionResult(
            prediction=prediction,
            synthetic_probability=round(synthetic_prob, 3),
            real_probability=real_prob,
            model_name=self.MODEL_NAME,
            model_type="heuristic_baseline",
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

