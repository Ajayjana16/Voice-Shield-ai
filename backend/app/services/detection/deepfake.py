"""
Voice Shield AI — Voice Authenticity & Anti-Spoofing Detection Engine.
Utilizes a trained multi-dimensional forensic acoustic classifier (MFCCs, spectral rolloff,
spectral flatness, high-frequency energy ratio, flux, and pitch jitter) to reliably distinguish
natural human speech from AI-generated/TTS/cloned voices.
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.fftpack import dct

from app.core.config import get_settings
from app.models.schemas import AcousticFeatures, DeepfakeDetectionResult
from app.services.audio.preprocessing import load_audio_resampled, validate_speech_activity

logger = logging.getLogger("voiceshield.authenticity")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "saved" / "deepfake_detector" / "forensic_voice_classifier.joblib"

_FORENSIC_CLASSIFIER_BUNDLE: dict[str, Any] | None = None


def get_forensic_classifier_bundle() -> dict[str, Any] | None:
    global _FORENSIC_CLASSIFIER_BUNDLE
    if _FORENSIC_CLASSIFIER_BUNDLE is None:
        if MODEL_PATH.exists():
            try:
                _FORENSIC_CLASSIFIER_BUNDLE = joblib.load(str(MODEL_PATH))
                logger.info("Successfully loaded Forensic Voice Authenticity Classifier from %s", MODEL_PATH)
            except Exception as e:
                logger.error("Failed to load forensic voice classifier: %s", e)
                _FORENSIC_CLASSIFIER_BUNDLE = None
        else:
            logger.warning("Forensic voice classifier file not found at %s", MODEL_PATH)
    return _FORENSIC_CLASSIFIER_BUNDLE


def extract_forensic_feature_vector(arr: np.ndarray, sr: int = 16000) -> np.ndarray | None:
    """
    Extracts a 40-dimensional acoustic forensic feature vector for anti-spoofing & synthetic voice detection.
    """
    if arr is None or len(arr) < int(0.20 * sr):
        return None

    arr = arr.astype(np.float32)
    peak = float(np.max(np.abs(arr)))
    if peak > 1e-6:
        arr = arr / peak

    rms = float(np.sqrt(np.mean(arr ** 2)))
    if rms < 0.001:
        return None

    n_fft = 512
    hop_length = 160  # 10ms
    win_length = 400  # 25ms

    num_frames = (len(arr) - win_length) // hop_length
    if num_frames < 4:
        return None

    # Windowed frames
    frames = np.lib.stride_tricks.sliding_window_view(arr[: num_frames * hop_length + win_length], win_length)[::hop_length]
    window = np.hanning(win_length)
    windowed = frames * window

    # RFFT Power Spectrum
    rfft = np.fft.rfft(windowed, n=n_fft, axis=1)
    mag = np.abs(rfft)
    power = mag ** 2
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

    # 1. Spectral Flatness
    gmean = np.exp(np.mean(np.log(power + 1e-12), axis=1))
    amean = np.mean(power, axis=1) + 1e-12
    flatness = gmean / amean
    flatness_mean = float(np.mean(flatness))
    flatness_std = float(np.std(flatness))

    # 2. Spectral Centroid
    centroid = np.sum(freqs * mag, axis=1) / (np.sum(mag, axis=1) + 1e-12)
    centroid_mean = float(np.mean(centroid))
    centroid_std = float(np.std(centroid))

    # 3. Spectral Rolloff (85% and 95%)
    cum_power = np.cumsum(power, axis=1)
    tot_power = cum_power[:, -1:] + 1e-12
    rolloff_85_idx = np.argmax(cum_power >= 0.85 * tot_power, axis=1)
    rolloff_95_idx = np.argmax(cum_power >= 0.95 * tot_power, axis=1)
    rolloff_85 = float(np.mean(freqs[rolloff_85_idx]))
    rolloff_95 = float(np.mean(freqs[rolloff_95_idx]))

    # 4. High-Frequency Energy Ratio (>4kHz vs <4kHz)
    hf_bins = freqs >= 4000
    lf_bins = (freqs >= 250) & (freqs < 4000)
    hf_energy = np.sum(power[:, hf_bins], axis=1)
    lf_energy = np.sum(power[:, lf_bins], axis=1) + 1e-12
    hf_ratio_mean = float(np.mean(hf_energy / lf_energy))
    hf_ratio_std = float(np.std(hf_energy / lf_energy))

    # 5. Spectral Flux
    diff_mag = np.diff(mag, axis=0)
    flux = float(np.mean(np.sqrt(np.sum(diff_mag ** 2, axis=1))))

    # 6. MFCCs (13 filterbank bands)
    n_mels = 13
    mel_min = 0.0
    mel_max = 2595.0 * np.log10(1.0 + (sr / 2.0) / 700.0)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    fbank = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]
        for k in range(f_m_minus, f_m):
            fbank[m - 1, k] = (k - bin_points[m - 1]) / max(1, bin_points[m] - bin_points[m - 1])
        for k in range(f_m, f_m_plus):
            fbank[m - 1, k] = (bin_points[m + 1] - k) / max(1, bin_points[m + 1] - bin_points[m])

    mel_energies = np.dot(power, fbank.T) + 1e-12
    log_mel = np.log(mel_energies)
    mfccs = dct(log_mel, type=2, axis=1, norm="ortho")
    mfcc_means = np.mean(mfccs, axis=0).tolist()
    mfcc_stds = np.std(mfccs, axis=0).tolist()

    # 7. Pitch & Vocal Jitter
    frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
    voiced = frame_rms > (rms * 0.3)
    pitches = []
    min_lag = int(sr / 400)
    max_lag = int(sr / 70)
    for f in frames[voiced]:
        c = np.correlate(f, f, mode="full")
        c = c[len(c) // 2 :]
        if max_lag < len(c):
            lag = min_lag + np.argmax(c[min_lag:max_lag])
            if c[lag] > 0.35 * c[0]:
                pitches.append(sr / lag)

    pitch_std = float(np.std(pitches)) if len(pitches) >= 5 else 0.0
    pitch_jitter = float(np.mean(np.abs(np.diff(pitches)))) if len(pitches) >= 8 else 0.0

    energy_cv = float(np.std(frame_rms) / (rms + 1e-6))
    zcr = float(np.mean(np.diff(np.signbit(arr)))) if len(arr) > 1 else 0.0

    vector = [
        flatness_mean, flatness_std,
        centroid_mean, centroid_std,
        rolloff_85, rolloff_95,
        hf_ratio_mean, hf_ratio_std,
        flux,
        pitch_std, pitch_jitter,
        energy_cv, zcr, rms,
    ] + mfcc_means + mfcc_stds

    return np.array(vector, dtype=np.float32)


class BaseDeepfakeDetector(ABC):
    @abstractmethod
    def detect(self, audio_path: Path | None, features: AcousticFeatures) -> DeepfakeDetectionResult:
        pass


class TrainedForensicVoiceDetector(BaseDeepfakeDetector):
    """
    Trained Anti-Spoofing & Synthetic Voice Detection Classifier.
    Evaluates acoustic, vocoder, and cepstral features against a trained calibrated ensemble.
    """
    MODEL_NAME = "VoiceShield-Forensic-Acoustic-v3"

    def detect(self, audio_path: Path | None, features: AcousticFeatures) -> DeepfakeDetectionResult:
        t0 = time.perf_counter()
        
        if not audio_path or not Path(audio_path).exists():
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.MODEL_NAME,
                model_type="trained_forensic_classifier",
                model_status="no_audio_file",
                model_inference_skipped=True,
                skip_reason="Audio file was not provided or does not exist on disk.",
                inference_time_ms=0.0,
                fallback_used=False,
                reasons=["Voice authenticity analysis unavailable: No audio file provided."],
            )

        # 1. Audio Preprocessing: Load & Resample to 16kHz
        try:
            audio_arr, sr = load_audio_resampled(Path(audio_path), target_sr=16000)
        except Exception as prep_err:
            logger.error("Audio preprocessing failed for %s: %s", audio_path, prep_err)
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.MODEL_NAME,
                model_type="trained_forensic_classifier",
                model_status="preprocessing_failed",
                model_inference_skipped=True,
                skip_reason=f"Failed to decode or resample audio: {prep_err}",
                inference_time_ms=0.0,
                fallback_used=False,
                reasons=[f"Voice authenticity analysis unavailable: Audio decoding error ({prep_err})."],
            )

        # 2. VAD & Speech Validation
        is_speech, reason, voiced_sec = validate_speech_activity(audio_arr, sr)
        if not is_speech:
            logger.info("Speech validation gate skipped analysis for %s: %s", audio_path, reason)
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.MODEL_NAME,
                model_type="trained_forensic_classifier",
                model_status="skipped",
                model_inference_skipped=True,
                skip_reason=reason,
                inference_time_ms=round((time.perf_counter() - t0) * 1000, 2),
                fallback_used=False,
                reasons=[f"Voice authenticity analysis unavailable: {reason}"],
            )

        # 3. Extract 40-D Forensic Feature Vector
        feat_vector = extract_forensic_feature_vector(audio_arr, sr)
        if feat_vector is None:
            return DeepfakeDetectionResult(
                prediction="INCONCLUSIVE",
                synthetic_probability=0.50,
                real_probability=0.50,
                model_name=self.MODEL_NAME,
                model_type="trained_forensic_classifier",
                model_status="insufficient_frames",
                model_inference_skipped=False,
                inference_time_ms=round((time.perf_counter() - t0) * 1000, 2),
                fallback_used=False,
                reasons=["Voice authenticity inconclusive: Insufficient acoustic frame density."],
            )

        # 4. Model Inference
        bundle = get_forensic_classifier_bundle()
        if bundle is None or "pipeline" not in bundle:
            logger.error("Forensic voice authenticity model bundle could not be loaded from disk.")
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.MODEL_NAME,
                model_type="trained_forensic_classifier",
                model_status="model_unavailable",
                model_inference_skipped=True,
                skip_reason="Model weights file missing or corrupt.",
                inference_time_ms=round((time.perf_counter() - t0) * 1000, 2),
                fallback_used=False,
                reasons=["Voice authenticity analysis unavailable: Model weights could not be loaded."],
            )

        pipeline = bundle["pipeline"]
        try:
            probs = pipeline.predict_proba([feat_vector])[0]
            synthetic_prob = float(probs[1])
            real_prob = float(probs[0])
        except Exception as inf_err:
            logger.error("Classifier inference failed: %s", inf_err)
            return DeepfakeDetectionResult(
                prediction="NOT_ANALYZED",
                synthetic_probability=0.0,
                real_probability=0.0,
                model_name=self.MODEL_NAME,
                model_type="trained_forensic_classifier",
                model_status="inference_failed",
                model_inference_skipped=True,
                skip_reason=str(inf_err),
                inference_time_ms=round((time.perf_counter() - t0) * 1000, 2),
                fallback_used=False,
                reasons=[f"Voice authenticity analysis failed during inference: {inf_err}"],
            )

        inference_ms = round((time.perf_counter() - t0) * 1000, 2)
        
        # 5. Calibration & Reason Generation
        reasons = []
        duration = len(audio_arr) / float(sr)
        
        if duration < 1.0:
            prediction = "INCONCLUSIVE"
            confidence = "LOW"
            reasons.append(f"Short recording duration ({duration:.2f}s). Classification confidence is reduced.")
        elif synthetic_prob >= 0.65:
            prediction = "SYNTHETIC"
            confidence = "HIGH" if synthetic_prob >= 0.85 else "MEDIUM"
            reasons.append(f"High-confidence synthetic vocoder and acoustic generation artifacts detected ({round(synthetic_prob * 100)}% synthetic probability).")
            if feat_vector[6] < 0.05:
                reasons.append("Elevated high-frequency spectral rolloff characteristic of neural vocoder cutoff filters.")
            if feat_vector[0] > 0.08:
                reasons.append("Elevated spectral flatness and phase noise indicating artificial carrier generation.")
        elif synthetic_prob >= 0.35:
            prediction = "INCONCLUSIVE"
            confidence = "UNCERTAIN"
            reasons.append(f"Acoustic features exhibit mixed characteristics ({round(synthetic_prob * 100)}% synthetic / {round(real_prob * 100)}% human probability).")
        else:
            prediction = "REAL"
            confidence = "HIGH" if real_prob >= 0.85 else "MEDIUM"
            reasons.append(f"Acoustic and prosodic dynamics match biological human vocal tract production ({round(real_prob * 100)}% human probability).")

        logger.info(
            f"[AUTHENTICITY AUDIT] File: {Path(audio_path).name} | Duration: {duration:.2f}s | "
            f"Synth Prob: {synthetic_prob:.3f} | Real Prob: {real_prob:.3f} | Verdict: {prediction} ({confidence}) | Time: {inference_ms:.1f}ms"
        )

        return DeepfakeDetectionResult(
            prediction=prediction,
            synthetic_probability=round(synthetic_prob, 3),
            real_probability=round(real_prob, 3),
            model_name=self.MODEL_NAME,
            model_type="trained_forensic_classifier",
            model_status="loaded",
            model_inference_skipped=False,
            inference_time_ms=inference_ms,
            fallback_used=False,
            reasons=reasons,
        )


def detect_synthetic_voice_detailed(features: AcousticFeatures, audio_path: Path | None = None) -> DeepfakeDetectionResult:
    detector = TrainedForensicVoiceDetector()
    return detector.detect(audio_path, features)


def detect_synthetic_voice(features: AcousticFeatures, audio_path: Path | None = None) -> tuple[float, list[str]]:
    result = detect_synthetic_voice_detailed(features, audio_path)
    return result.synthetic_probability, result.reasons


# Backward-compatible aliases for legacy imports
ExplainableAcousticDetector = TrainedForensicVoiceDetector
PretrainedAntiSpoofAdapter = TrainedForensicVoiceDetector
