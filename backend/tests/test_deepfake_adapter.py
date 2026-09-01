import math
import tempfile
import wave
from pathlib import Path
import numpy as np

from app.models.schemas import AcousticFeatures
from app.services.detection.deepfake import (
    TrainedForensicVoiceDetector,
    ExplainableAcousticDetector,
    PretrainedAntiSpoofAdapter,
    detect_synthetic_voice,
    detect_synthetic_voice_detailed,
)


def test_explainable_acoustic_detector_clean_voice(tmp_path):
    detector = TrainedForensicVoiceDetector()
    sr = 16000
    dur = 2.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    # Simulated natural voice with harmonic variations
    sig = 0.4 * np.sin(2 * np.pi * 150 * t) + 0.1 * np.sin(2 * np.pi * 300 * t)
    
    import soundfile as sf
    wav_path = tmp_path / "voice.wav"
    sf.write(str(wav_path), sig, sr)

    features = AcousticFeatures(
        duration_seconds=dur,
        sample_rate=sr,
        rms_energy=0.12,
        zero_crossing_rate=0.08,
        spectral_centroid=1800.0,
        spectral_contrast=0.14,
        pitch_hz=165.0,
        pause_ratio=0.18,
        dynamic_range=0.45,
        byte_entropy=0.55,
    )
    result = detector.detect(wav_path, features)
    assert hasattr(result, "synthetic_probability")
    assert hasattr(result, "real_probability")
    assert result.model_status == "loaded"


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


def test_pretrained_adapter_graceful_handling():
    detector = TrainedForensicVoiceDetector()
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
    res = detector.detect(Path("non_existent_file.wav"), features)
    assert res.prediction == "NOT_ANALYZED"
    assert res.model_inference_skipped is True
