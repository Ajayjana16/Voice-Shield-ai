import io
import wave
import numpy as np
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.services.stt.social_engineering import analyze_context_detailed
from app.services.risk.scoring import calculate_risk_detailed
from app.services.analysis import analyze_audio_file


def _generate_synthetic_tone_wav(duration_sec: float = 1.0, freq: float = 440.0, sr: int = 16000) -> Path:
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    audio_data = (0.5 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)).astype(np.float32)
    pcm_data = (audio_data * 32767).astype(np.int16)

    tmp = NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm_data.tobytes())
    return Path(tmp.name)


def _generate_silence_wav(duration_sec: float = 1.0, sr: int = 16000) -> Path:
    pcm_data = np.zeros(int(sr * duration_sec), dtype=np.int16)
    tmp = NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm_data.tobytes())
    return Path(tmp.name)


def test_user_scenario_1_otp_request():
    transcript = "Tell me the OTP sent to your mobile."
    res = analyze_context_detailed(transcript)
    assert res["risk_level"] in ("HIGH", "CRITICAL")
    assert "OTP" in res["possible_scam_category"] or "Credential" in res["possible_scam_category"]
    assert res["context_risk_score"] >= 70

    score, level, rec, _ = calculate_risk_detailed(
        deepfake_probability=0.10,
        prosody_score=0.15,
        speaker_mismatch=0.0,
        context_risk=res["context_risk"],
        detected_indicators=res["detected_indicators"],
    )
    assert score >= 70
    assert level in ("HIGH", "CRITICAL")


def test_user_scenario_2_bank_and_transfer_pressure():
    transcript = "Transfer 50,000 rupees immediately or your account will be blocked."
    res = analyze_context_detailed(transcript)
    assert res["risk_level"] in ("HIGH", "CRITICAL")
    assert res["context_risk_score"] >= 70

    score, level, _, _ = calculate_risk_detailed(
        deepfake_probability=0.12,
        prosody_score=0.10,
        speaker_mismatch=0.0,
        context_risk=res["context_risk"],
        detected_indicators=res["detected_indicators"],
    )
    assert score >= 75
    assert level in ("HIGH", "CRITICAL")


def test_user_scenario_3_digital_arrest_authority_scam():
    transcript = "This is CBI. You are under digital arrest. Do not disconnect the call."
    res = analyze_context_detailed(transcript)
    assert res["risk_level"] == "CRITICAL"
    assert "Digital Arrest" in res["possible_scam_category"]

    score, level, _, _ = calculate_risk_detailed(
        deepfake_probability=0.15,
        prosody_score=0.10,
        speaker_mismatch=0.0,
        context_risk=res["context_risk"],
        detected_indicators=res["detected_indicators"],
    )
    assert score >= 85
    assert level == "CRITICAL"


def test_user_scenario_4_investment_guaranteed_returns():
    transcript = "Please invest today. You will receive guaranteed returns."
    res = analyze_context_detailed(transcript)
    assert res["risk_level"] in ("HIGH", "CRITICAL")
    assert "Investment" in res["possible_scam_category"] or "Advance Fee" in res["possible_scam_category"]

    score, level, _, _ = calculate_risk_detailed(
        deepfake_probability=0.10,
        prosody_score=0.10,
        speaker_mismatch=0.0,
        context_risk=res["context_risk"],
        detected_indicators=res["detected_indicators"],
    )
    assert score >= 70
    assert level in ("HIGH", "CRITICAL")


def test_user_scenario_5_routine_normal_conversation():
    transcript = "Hello team, please review the project documentation before tomorrow's meeting."
    res = analyze_context_detailed(transcript)
    assert res["risk_level"] == "LOW"
    assert res["context_risk"] == 0.0
    assert "Routine" in res["possible_scam_category"]


def test_user_scenario_6_silence_input():
    silence_path = _generate_silence_wav(1.5)
    try:
        res = analyze_audio_file(silence_path)
        assert res.analysis_status == "insufficient_audio"
        assert res.speech_detected is False
        assert res.risk_level == "NOT_ANALYZED"
        assert res.final_risk_score is None
    finally:
        silence_path.unlink(missing_ok=True)


def test_user_scenario_7_speech_detected_no_transcript():
    audio_path = _generate_synthetic_tone_wav(1.0)
    try:
        res = analyze_audio_file(audio_path, transcript=None)
        assert res.speech_detected is True
        assert res.analysis_status in ("partial_analysis", "completed")
        if res.analysis_status == "partial_analysis":
            assert res.risk_level == "PARTIAL_ANALYSIS"
            assert "Routine" not in (res.possible_scam_category or "")
    finally:
        audio_path.unlink(missing_ok=True)


def test_high_severity_indicator_cannot_produce_low_risk():
    score, level, _, _ = calculate_risk_detailed(
        deepfake_probability=0.25,
        prosody_score=0.30,
        speaker_mismatch=0.0,
        context_risk=0.85,
        detected_indicators=[{"category": "CREDENTIAL_OTP", "severity": "CRITICAL"}],
    )
    assert score >= 80
    assert level in ("HIGH", "CRITICAL")
