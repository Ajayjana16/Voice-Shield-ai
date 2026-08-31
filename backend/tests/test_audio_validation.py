import math
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.analysis import analyze_audio_file
from app.services.audio.preprocessing import validate_speech_activity

client = TestClient(app)


def _create_wav(samples: list[int] | np.ndarray, sample_rate: int = 16000) -> Path:
    if isinstance(samples, np.ndarray):
        int_samples = (samples * 32767).astype(np.int16).tolist()
    else:
        int_samples = samples
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        path = Path(handle.name)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(int(sample).to_bytes(2, "little", signed=True) for sample in int_samples))
    return path


def test_vad_pure_silence():
    samples = np.zeros(16000 * 2, dtype=np.float32)
    is_speech, reason, voiced_sec = validate_speech_activity(samples, 16000)
    assert not is_speech
    assert voiced_sec == 0.0


def test_vad_near_silent_noise():
    samples = np.random.normal(0, 0.001, 16000 * 2).astype(np.float32)
    is_speech, reason, voiced_sec = validate_speech_activity(samples, 16000)
    assert not is_speech


def test_vad_short_audio():
    samples = np.sin(2 * np.pi * 200 * np.linspace(0, 0.15, int(16000 * 0.15))).astype(np.float32)
    is_speech, reason, _ = validate_speech_activity(samples, 16000, min_duration_sec=0.35)
    assert not is_speech
    assert "too short" in reason.lower()


def test_pipeline_pure_silence_returns_insufficient_audio():
    path = _create_wav(np.zeros(16000 * 3, dtype=np.float32))
    try:
        response = analyze_audio_file(path)
        assert response.analysis_status == "insufficient_audio"
        assert response.speech_detected is False
        assert response.model_inference_skipped is True
        assert response.skip_reason == "insufficient_speech_audio"
        assert response.final_risk_score is None
        assert response.risk_level == "NOT_ANALYZED"
        assert response.prediction == "NOT_ANALYZED"
        assert len(response.detected_threats) == 0
    finally:
        path.unlink(missing_ok=True)


def test_pipeline_quiet_noise_does_not_produce_high_risk():
    path = _create_wav(np.random.normal(0, 0.001, 16000 * 3).astype(np.float32))
    try:
        response = analyze_audio_file(path)
        assert response.analysis_status == "insufficient_audio"
        assert response.speech_detected is False
        assert response.final_risk_score is None
        assert response.risk_level == "NOT_ANALYZED"
    finally:
        path.unlink(missing_ok=True)


def test_api_audio_chunk_silence_handling():
    path = _create_wav(np.zeros(16000 * 2, dtype=np.float32))
    try:
        with path.open("rb") as audio_file:
            res = client.post(
                "/api/audio/chunk",
                files={"file": ("chunk_silence.wav", audio_file, "audio/wav")},
            )
        assert res.status_code == 200
        data = res.json()
        assert data["analysis_status"] == "insufficient_audio"
        assert data["speech_detected"] is False
        assert data["final_risk_score"] is None
        assert data["risk_level"] == "NOT_ANALYZED"
        assert data["rolling_stats"]["trend"] == "WAITING_FOR_SPEECH"
    finally:
        path.unlink(missing_ok=True)
