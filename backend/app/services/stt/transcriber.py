from pathlib import Path
import os

from app.models.schemas import SttResponse

_whisper_model = None
_model_attempted = False

def transcribe_audio(path: Path) -> SttResponse:
    global _whisper_model, _model_attempted
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return SttResponse(
            transcript="",
            provider="manual-transcript-required",
            confidence=0.0,
            warning="Server-side STT is not installed. Use browser dictation or paste transcript text.",
        )

    if _whisper_model is None and not _model_attempted:
        _model_attempted = True
        try:
            _whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2, local_files_only=True)
        except Exception:
            _whisper_model = None

    if _whisper_model is None:
        return SttResponse(
            transcript="",
            provider="faster-whisper/unavailable",
            confidence=0.0,
            warning="Local Whisper model is not loaded. Browser speech-to-text active.",
        )

    try:
        segments, info = _whisper_model.transcribe(str(path), beam_size=1)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        confidence = max(0.0, min(1.0, 1.0 - float(getattr(info, "language_probability", 0.0))))
        return SttResponse(transcript=transcript, provider="faster-whisper/tiny.en", confidence=round(confidence, 3))
    except Exception as error:
        return SttResponse(
            transcript="",
            provider="faster-whisper/tiny.en",
            confidence=0.0,
            warning=f"Transcription failed: {error}",
        )
