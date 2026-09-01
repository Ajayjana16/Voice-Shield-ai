import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from app.models.schemas import SttResponse

logger = logging.getLogger(__name__)

_whisper_model: Any = None
_model_attempted: bool = False


def _get_whisper_model() -> Any:
    global _whisper_model, _model_attempted
    if _whisper_model is not None:
        return _whisper_model

    if _model_attempted:
        return None

    _model_attempted = True
    try:
        from faster_whisper import WhisperModel

        model_size = os.getenv("STT_MODEL_SIZE", "tiny.en")
        cpu_threads = int(os.getenv("STT_CPU_THREADS", "2"))
        logger.info(f"Initializing faster-whisper model ({model_size}) on CPU...")
        _whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
        )
        logger.info("faster-whisper model initialized successfully.")
        return _whisper_model
    except Exception as e:
        logger.warning(f"Could not initialize faster-whisper model: {e}")
        _whisper_model = None
        return None


def transcribe_audio(path: Path) -> SttResponse:
    """
    Transcribes spoken audio from a file path using CPU-optimized faster-whisper.
    Supports .wav, .mp3, .m4a, .ogg, .webm formats with fallback numpy array decoding.
    """
    if not path.exists():
        return SttResponse(
            transcript="",
            provider="faster-whisper/error",
            confidence=0.0,
            warning=f"Audio file not found: {path.name}",
        )

    model = _get_whisper_model()
    if model is None:
        return SttResponse(
            transcript="",
            provider="faster-whisper/unavailable",
            confidence=0.0,
            warning="Server-side Speech-to-Text engine could not be initialized. Please check backend dependencies.",
        )

    model_name = getattr(model, "model_size_or_path", "tiny.en")
    provider_str = f"faster-whisper/{model_name}"

    try:
        # Primary Strategy: Direct file transcription (PyAV handles wav/mp3/m4a/ogg/webm)
        segments, info = model.transcribe(
            str(path),
            beam_size=1,
            language="en",
            condition_on_previous_text=False,
        )
        text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        transcript = " ".join(text_parts).strip()

        if transcript:
            lang_prob = float(getattr(info, "language_probability", 0.95))
            confidence = round(max(0.5, min(1.0, lang_prob)), 3)
            return SttResponse(
                transcript=transcript,
                provider=provider_str,
                confidence=confidence,
            )
    except Exception as direct_err:
        logger.warning(f"Direct faster-whisper transcription notice ({direct_err}), trying audio array decoding...")

    # Secondary Strategy: Load and resample to 16kHz float32 numpy array
    try:
        from app.services.audio.preprocessing import load_audio_resampled
        import numpy as np

        samples, sr = load_audio_resampled(path, target_sr=16000)
        if isinstance(samples, np.ndarray) and len(samples) > 1600:
            segments, info = model.transcribe(
                samples,
                beam_size=1,
                language="en",
                condition_on_previous_text=False,
            )
            text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
            transcript = " ".join(text_parts).strip()

            if transcript:
                lang_prob = float(getattr(info, "language_probability", 0.95))
                confidence = round(max(0.5, min(1.0, lang_prob)), 3)
                return SttResponse(
                    transcript=transcript,
                    provider=provider_str,
                    confidence=confidence,
                )
    except Exception as resample_err:
        logger.error(f"Resampled transcription failed: {resample_err}")

    return SttResponse(
        transcript="",
        provider=provider_str,
        confidence=0.0,
        warning="No audible speech could be transcribed from the audio file.",
    )
