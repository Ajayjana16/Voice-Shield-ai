import math
import tempfile
import wave
from pathlib import Path

from app.models.schemas import AcousticFeatures
from app.services.detection.deepfake import (
    ExplainableAcousticDetector,
    PretrainedAntiSpoofAdapter,
    detect_synthetic_voice,
    detect_synthetic_voice_detailed,
)


def test_explainable_acoustic_detector_clean_voice():
    features = AcousticFeatures(
        duration_seconds=3.0,
        sample_rate=16000,
        rms_energy=0.12,
        zero_crossing_rate=0.08,
        spectral_centroid=1800.0,
        spectral_contrast=0.14,
        pitch_hz=165.0,
        pause_ratio=0.18,
        dynamic_range=0.45,
        byte_entropy=0.55,
    )
    detector = ExplainableAcousticDetector()
    result = detector.detect(None, features)

    assert result.prediction == "REAL"
    assert result.synthetic_probability < 0.30
    assert result.real_probability > 0.70
    assert result.fallback_used is True
    assert result.model_name == "VoiceShield-Acoustic-v2"
    assert result.inference_time_ms >= 0.0


def test_explainable_acoustic_detector_synthetic_artifacts():
    # Anomalous high-frequency carrier and low dynamic range
    features = AcousticFeatures(
        duration_seconds=3.0,
        sample_rate=16000,
        rms_energy=0.08,
        zero_crossing_rate=0.45,
        spectral_centroid=5800.0,
        spectral_contrast=0.001,
        pitch_hz=210.0,
        pause_ratio=0.03,
        dynamic_range=0.03,
        byte_entropy=0.98,
    )
    detector = ExplainableAcousticDetector()
    result = detector.detect(None, features)

    assert result.synthetic_probability >= 0.35
    assert len(result.reasons) >= 2
    assert result.fallback_used is True


def test_detect_synthetic_voice_entrypoints():
    features = AcousticFeatures(
        duration_seconds=2.0,
        sample_rate=16000,
        rms_energy=0.09,
        zero_crossing_rate=0.07,
        spectral_centroid=1600.0,
        spectral_contrast=0.12,
        pitch_hz=140.0,
        pause_ratio=0.15,
        dynamic_range=0.35,
        byte_entropy=0.50,
    )
    # Detailed result
    detailed = detect_synthetic_voice_detailed(features)
    assert hasattr(detailed, "synthetic_probability")
    assert hasattr(detailed, "inference_time_ms")

    # Backward compatible tuple
    prob, reasons = detect_synthetic_voice(features)
    assert isinstance(prob, float)
    assert isinstance(reasons, list)


def test_pretrained_adapter_graceful_fallback():
    # Model that doesn't exist should gracefully return None without crashing
    adapter = PretrainedAntiSpoofAdapter("non-existent/model-id-12345")
    features = AcousticFeatures(
        duration_seconds=1.0,
        sample_rate=16000,
        rms_energy=0.1,
        zero_crossing_rate=0.1,
        spectral_centroid=1500.0,
        spectral_contrast=0.1,
        pitch_hz=150.0,
        pause_ratio=0.2,
        dynamic_range=0.3,
        byte_entropy=0.5,
    )
    res = adapter.detect(Path("non_existent_file.wav"), features)
    assert res is None

