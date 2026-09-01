import io
import struct
from pathlib import Path
import numpy as np
import pytest

from app.models.schemas import AcousticFeatures
from app.services.audio.preprocessing import load_audio, extract_features
from app.services.detection.deepfake import detect_synthetic_voice_detailed, TrainedForensicVoiceDetector


def _make_synthetic_sample(sr=16000, duration=3.0, freq=300):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Monotone with high-frequency noise & vocoder flatness
    sig = 0.3 * np.sin(2 * np.pi * freq * t) + 0.05 * np.random.normal(0, 0.1, len(t))
    return sig.astype(np.float32)


def test_eval_benchmarks_distinction():
    """Verify that genuine human and synthetic samples in benchmarks are correctly classified."""
    detector = TrainedForensicVoiceDetector()
    bench_dir = Path("../data/temp/eval_benchmarks")
    if not bench_dir.exists():
        pytest.skip("Benchmark directory not found")

    # Test Genuine samples
    for gen_file in bench_dir.glob("genuine_*.wav"):
        if "short" in gen_file.name:
            continue
        feats = extract_features(load_audio(gen_file))
        result = detector.detect(gen_file, feats)
        assert result.prediction == "REAL"
        assert result.real_probability > result.synthetic_probability
        assert result.synthetic_probability < 0.35

    # Test Synthetic samples
    for syn_file in bench_dir.glob("synthetic_*.wav"):
        if "short" in syn_file.name:
            continue
        feats = extract_features(load_audio(syn_file))
        result = detector.detect(syn_file, feats)
        assert result.prediction == "SYNTHETIC"
        assert result.synthetic_probability > result.real_probability
        assert result.synthetic_probability >= 0.70


def test_short_audio_inconclusive(tmp_path):
    """Audio shorter than 1s must produce INCONCLUSIVE verdict."""
    detector = TrainedForensicVoiceDetector()
    sr = 16000
    dur = 0.6
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    sig = 0.4 * np.sin(2 * np.pi * 200 * t)
    
    # Write wav
    import soundfile as sf
    wav_path = tmp_path / "short.wav"
    sf.write(str(wav_path), sig, sr)

    feats = extract_features(load_audio(wav_path))
    result = detector.detect(wav_path, feats)
    assert result.prediction == "INCONCLUSIVE"


def test_silent_audio_skipped(tmp_path):
    """Silent or near-silent audio must be skipped by the speech validation gate."""
    detector = TrainedForensicVoiceDetector()
    sr = 16000
    dur = 2.0
    sig = np.zeros(int(sr * dur), dtype=np.float32)
    
    import soundfile as sf
    wav_path = tmp_path / "silence.wav"
    sf.write(str(wav_path), sig, sr)

    feats = extract_features(load_audio(wav_path))
    result = detector.detect(wav_path, feats)
    assert result.model_inference_skipped is True
    assert result.prediction == "NOT_ANALYZED"


def test_corrupted_audio_handling(tmp_path):
    """Corrupted audio files must fail gracefully with NOT_ANALYZED, not crash."""
    detector = TrainedForensicVoiceDetector()
    corrupt_path = tmp_path / "corrupt.wav"
    corrupt_path.write_bytes(b"RIFFcorruptedtrashdata12345678")

    dummy_feats = AcousticFeatures(
        duration_seconds=0.0,
        sample_rate=16000,
        rms_energy=0.0,
        zero_crossing_rate=0.0,
        spectral_centroid=0.0,
        spectral_contrast=0.0,
        pitch_hz=0.0,
        pause_ratio=1.0,
        dynamic_range=0.0,
        byte_entropy=0.0,
    )
    result = detector.detect(corrupt_path, dummy_feats)
    assert result.prediction == "NOT_ANALYZED" or result.model_inference_skipped is True
