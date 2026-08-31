import math
import tempfile
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "healthy"]


def test_context_endpoint() -> None:
    response = client.post(
        "/api/context/analyze",
        json={"transcript": "Urgent transfer request. Send the OTP and do not tell anyone."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["context_risk"] >= 0.75
    assert payload["risk_level"] == "CRITICAL"


def test_audio_chunk_endpoint() -> None:
    path = _write_demo_wav()
    try:
        with path.open("rb") as audio_file:
            response = client.post(
                "/api/audio/chunk",
                files={"file": ("chunk.wav", audio_file, "audio/wav")},
                data={"transcript": "normal project update"},
            )
        assert response.status_code == 200
        assert "analysis_id" in response.json()
    finally:
        path.unlink(missing_ok=True)


def _write_demo_wav() -> Path:
    sample_rate = 16000
    samples = [
        int(math.sin(2 * math.pi * 180 * index / sample_rate) * 12000)
        for index in range(sample_rate // 2)
    ]
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        path = Path(handle.name)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return path
