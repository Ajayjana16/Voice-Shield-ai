import math
from pathlib import Path
from typing import Any

from app.models.schemas import AcousticFeatures, SpeakerVerificationResult
from app.services.audio.preprocessing import load_audio_resampled, validate_speech_activity

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False


# Default threshold for declaring biometric match
SPEAKER_MATCH_THRESHOLD = 0.70


def extract_speaker_embedding(
    path: Path | None = None,
    features: AcousticFeatures | None = None,
) -> list[float]:
    if path and path.exists() and _HAS_NUMPY and np is not None:
        try:
            samples, sr = load_audio_resampled(path, target_sr=16000)
            is_speech, _, _ = validate_speech_activity(samples, sr, min_duration_sec=0.25, min_voiced_duration_sec=0.15)
            if is_speech and len(samples) >= 1600:
                return _compute_spectral_embedding(samples, sr)
        except Exception:
            pass

    # Fallback to acoustic features vector
    if features is not None and features.rms_energy >= 0.0030 and features.dynamic_range >= 0.015:
        return _embedding_from_features_extended(features)

    # Empty fallback for silence / non-speech
    return [0.0] * 64


def _compute_spectral_embedding(samples: Any, sr: int, num_bands: int = 64) -> list[float]:
    n_fft = 1024
    hop_length = 512
    if len(samples) < n_fft:
        samples = np.pad(samples, (0, n_fft - len(samples)), mode="constant")

    # Compute Short-Time Fourier Transform (STFT) frames
    num_frames = max(1, (len(samples) - n_fft) // hop_length + 1)
    frames = np.lib.stride_tricks.sliding_window_view(
        samples[:num_frames * hop_length + n_fft - hop_length], window_shape=n_fft
    )[::hop_length]
    window = np.hanning(n_fft)
    spec = np.abs(np.fft.rfft(frames * window, axis=1))

    # 1. Harmonic spectral profile across lower and mid frequency bins (48 bins)
    n_bins = min(48, spec.shape[1])
    harmonic_profile = np.mean(spec[:, :n_bins], axis=0)

    # Peak normalize and suppress low-energy noise floor
    peak = np.max(harmonic_profile)
    if peak > 0:
        harmonic_profile = harmonic_profile / peak
    harmonic_profile = np.where(harmonic_profile > 0.06, harmonic_profile, 0.0)

    if len(harmonic_profile) < 48:
        harmonic_profile = np.pad(harmonic_profile, (0, 48 - len(harmonic_profile)))
    else:
        harmonic_profile = harmonic_profile[:48]

    # 2. Autocorrelation pitch fundamental proxy (16 bins)
    autocorr = np.correlate(samples[:min(len(samples), sr)], samples[:min(len(samples), sr)], mode="full")
    autocorr = autocorr[len(autocorr) // 2 :]
    lags = autocorr[int(sr / 400) : int(sr / 70)]
    pitch_hz = float(sr / (np.argmax(lags) + int(sr / 400))) if len(lags) > 0 else 150.0

    pitch_vec = np.zeros(16, dtype=np.float32)
    bin_idx = int(min(15, max(0, (pitch_hz - 70) / (400 - 70) * 16)))
    pitch_vec[bin_idx] = 1.0

    combined = np.concatenate([harmonic_profile, pitch_vec * 2.0])
    norm = np.linalg.norm(combined)
    if norm > 1e-9:
        combined = combined / norm

    return combined.tolist()


def _embedding_from_features_extended(features: AcousticFeatures) -> list[float]:
    base = [
        _scale(features.pitch_hz, 70, 360),
        min(features.rms_energy * 8, 1),
        min(features.zero_crossing_rate * 4, 1),
        min(features.spectral_centroid / 4000, 1),
        min(features.spectral_contrast * 8, 1),
        min(features.dynamic_range, 1),
        min(features.pause_ratio, 1),
        features.byte_entropy,
    ]
    expanded = []
    for i in range(8):
        for val in base:
            expanded.append(val * (0.85 ** i))
    
    norm = math.sqrt(sum(v * v for v in expanded))
    if norm > 1e-9:
        return [v / norm for v in expanded]
    return expanded


def embedding_from_features(features: AcousticFeatures) -> list[float]:
    return extract_speaker_embedding(features=features)


def similarity(current: list[float], reference: list[float]) -> float:
    if not current or not reference or len(current) != len(reference):
        return 0.0
    dot = sum(left * right for left, right in zip(current, reference))
    left_norm = math.sqrt(sum(value * value for value in current))
    right_norm = math.sqrt(sum(value * value for value in reference))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def verify_speaker_identity(
    current_embedding: list[float],
    reference_embedding: list[float],
    threshold: float = SPEAKER_MATCH_THRESHOLD,
) -> SpeakerVerificationResult:
    # Check if current embedding is all zeros (silence)
    if not any(v > 1e-6 for v in current_embedding):
        return SpeakerVerificationResult(
            speaker_match_score=0,
            speaker_match=False,
            similarity=0.0,
            confidence=0.0,
            speaker_mismatch=0.0,  # Do not penalize with 1.0 mismatch when silence was passed
        )

    sim = similarity(current_embedding, reference_embedding)
    
    if sim >= threshold:
        calibrated_score = 60 + int((sim - threshold) / (1.0 - threshold + 1e-9) * 40)
    else:
        calibrated_score = int((sim / threshold) * 60)
    calibrated_score = max(0, min(100, calibrated_score))

    is_match = sim >= threshold
    mismatch = round(1.0 - sim, 3)
    if is_match:
        confidence = 0.50 + ((sim - threshold) / (1.0 - threshold + 1e-9)) * 0.49
    else:
        confidence = 0.50 + ((threshold - sim) / (threshold + 1e-9)) * 0.49

    return SpeakerVerificationResult(
        speaker_match_score=calibrated_score,
        speaker_match=is_match,
        similarity=round(sim, 3),
        confidence=round(min(max(confidence, 0.1), 0.99), 3),
        speaker_mismatch=mismatch,
    )


def _scale(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
