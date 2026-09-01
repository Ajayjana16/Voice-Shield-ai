import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.stt.transcriber import transcribe_audio

client = TestClient(app)

def test_transcribe_nonexistent_file():
    res = transcribe_audio(Path('nonexistent_audio_file.wav'))
    assert res.transcript == ''
    assert 'not found' in res.warning.lower()

def test_stt_endpoint():
    sample_wav = Path(r'data/sample_audio/demo-call.wav')
    if not sample_wav.exists():
        sample_wav = Path(r'../data/sample_audio/demo-call.wav')
    
    assert sample_wav.exists()
    with sample_wav.open('rb') as f:
        res = client.post('/api/stt/transcribe', files={'file': ('demo-call.wav', f, 'audio/wav')})
    assert res.status_code == 200
    data = res.json()
    assert 'transcript' in data
    assert len(data['transcript']) > 0
    assert 'faster-whisper' in data['provider']

def test_audio_analyze_auto_stt():
    sample_wav = Path(r'data/sample_audio/demo-call.wav')
    if not sample_wav.exists():
        sample_wav = Path(r'../data/sample_audio/demo-call.wav')

    with sample_wav.open('rb') as f:
        res = client.post('/api/audio/analyze', files={'file': ('demo-call.wav', f, 'audio/wav')})
    assert res.status_code == 200
    data = res.json()
    assert data['transcript'] is not None
    assert len(data['transcript']) > 0
    assert data['analysis_status'] == 'completed'
