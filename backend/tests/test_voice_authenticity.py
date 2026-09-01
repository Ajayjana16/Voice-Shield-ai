import io
import struct
from pathlib import Path
import numpy as np
import pytest

from app.models.schemas import AcousticFeatures, DetectedContextIndicator
from app.services.audio.preprocessing import load_audio, extract_features
from app.services.decision_engine import evaluate_centralized_security_decision
from app.services.detection.deepfake import (
    DeepfakeDetectionResult,
    detect_synthetic_voice_detailed,
    TrainedForensicVoiceDetector,
)


def _make_synthetic_sample(sr=16000, duration=3.0, freq=300):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
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


def test_centralized_decision_engine_synthetic_escalation():
    """Verify that synthetic voice detection forces overall risk escalation and consistency."""
    dummy_feats = AcousticFeatures(
        duration_seconds=3.0,
        sample_rate=16000,
        rms_energy=0.1,
        zero_crossing_rate=0.1,
        spectral_centroid=2000.0,
        spectral_contrast=0.1,
        pitch_hz=150.0,
        pause_ratio=0.1,
        dynamic_range=0.3,
        byte_entropy=0.5,
    )

    # 1. High Synthetic Prob (0.97) -> CRITICAL RISK
    df_res_97 = DeepfakeDetectionResult(
        prediction="SYNTHETIC",
        synthetic_probability=0.97,
        real_probability=0.03,
        model_name="VoiceShield-Forensic-Acoustic-v3",
    )
    decision_97 = evaluate_centralized_security_decision(
        df_result=df_res_97,
        features=dummy_feats,
        transcript="Hello, I am calling regarding your account.",
        detected_scam_indicators=[],
        context_risk=0.0,
        prosody_score=0.1,
        speaker_mismatch=0.0,
        has_speaker_ref=False,
    )
    assert decision_97["voice_auth_label"] == "Likely Synthetic / AI Generated"
    assert decision_97["overall_risk"] == "CRITICAL RISK"
    assert decision_97["threat_score"] >= 85
    assert "Synthetic / Cloned Voice Artifact" in decision_97["detected_threats"]
    assert decision_97["scam_category"] == "Synthetic / Cloned Voice Interaction"

    # 2. Moderate Synthetic Prob (0.75) -> MEDIUM RISK
    df_res_75 = DeepfakeDetectionResult(
        prediction="SYNTHETIC",
        synthetic_probability=0.75,
        real_probability=0.25,
        model_name="VoiceShield-Forensic-Acoustic-v3",
    )
    decision_75 = evaluate_centralized_security_decision(
        df_result=df_res_75,
        features=dummy_feats,
        transcript="Routine conversation with no keywords.",
        detected_scam_indicators=[],
        context_risk=0.0,
        prosody_score=0.1,
        speaker_mismatch=0.0,
        has_speaker_ref=False,
    )
    assert decision_75["voice_auth_label"] == "Likely Synthetic / AI Generated"
    assert decision_75["overall_risk"] == "MEDIUM RISK"
    assert decision_75["threat_score"] >= 50
    assert "Synthetic / Cloned Voice Artifact" in decision_75["detected_threats"]

    # 3. Clean Human Prob (0.05) -> LOW RISK
    df_res_human = DeepfakeDetectionResult(
        prediction="REAL",
        synthetic_probability=0.05,
        real_probability=0.95,
        model_name="VoiceShield-Forensic-Acoustic-v3",
    )
    decision_human = evaluate_centralized_security_decision(
        df_result=df_res_human,
        features=dummy_feats,
        transcript="Just checking in on the project status.",
        detected_scam_indicators=[],
        context_risk=0.0,
        prosody_score=0.1,
        speaker_mismatch=0.0,
        has_speaker_ref=False,
    )
    assert decision_human["voice_auth_label"] == "Likely Human"
    assert decision_human["overall_risk"] == "LOW RISK"
    assert "Synthetic / Cloned Voice Artifact" not in decision_human["detected_threats"]
    assert decision_human["scam_category"] != "Synthetic / Cloned Voice Interaction"
