import logging
import os
import time
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
        logger.info(f"Initializing faster-whisper model ({model_size}) on CPU with {cpu_threads} threads...")
        t0 = time.perf_counter()
        _whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
        )
        logger.info(f"faster-whisper model initialized in {(time.perf_counter() - t0) * 1000:.1f}ms.")
        return _whisper_model
    except Exception as e:
        logger.warning(f"Could not initialize faster-whisper model: {e}")
        _whisper_model = None
        return None


def preload_and_warmup_stt() -> None:
    """
    Preloads the faster-whisper model into memory and runs a tiny warm-up inference
    so that the first user request experiences zero cold-start delay.
    """
    try:
        model = _get_whisper_model()
        if model is not None:
            import numpy as np

            # 0.2s of 16kHz silence for compute kernel warm-up
            dummy_samples = np.zeros(3200, dtype=np.float32)
            t0 = time.perf_counter()
            segments, _ = model.transcribe(
                dummy_samples,
                beam_size=1,
                language="en",
                condition_on_previous_text=False,
            )
            list(segments)  # evaluate generator
            logger.info(f"faster-whisper warm-up completed in {(time.perf_counter() - t0) * 1000:.1f}ms.")
    except Exception as e:
        logger.warning(f"STT warm-up notice: {e}")


def transcribe_audio(
    path: Path | None = None,
    samples: Any = None,
) -> SttResponse:
    """
    Transcribes spoken audio using CPU-optimized faster-whisper.
    Accepts either an in-memory 16kHz float32 NumPy array or a file path.
    Supports .wav, .mp3, .m4a, .ogg, .webm formats with zero-copy in-memory execution.
    """
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

    # Strategy 1: Direct in-memory 16kHz NumPy array (Zero disk I/O)
    if samples is not None:
        try:
            import numpy as np

            arr = samples if isinstance(samples, np.ndarray) else np.array(samples, dtype=np.float32)
            if len(arr) > 1600:
                segments, info = model.transcribe(
                    arr,
                    beam_size=1,
                    language="en",
                    vad_filter=True,
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
        except Exception as arr_err:
            logger.warning(f"In-memory STT transcription notice ({arr_err}), falling back to file path...")

    if path is None or not path.exists():
        return SttResponse(
            transcript="",
            provider="faster-whisper/error",
            confidence=0.0,
            warning="Audio input not provided or file not found.",
        )

    # Strategy 2: Direct file transcription (PyAV handles wav/mp3/m4a/ogg/webm)
    try:
        segments, info = model.transcribe(
            str(path),
            beam_size=1,
            language="en",
            vad_filter=True,
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

    # Strategy 3: Resample and transcribe
    try:
        from app.services.audio.preprocessing import load_audio_resampled
        import numpy as np

        loaded_samples, sr = load_audio_resampled(path, target_sr=16000)
        if isinstance(loaded_samples, np.ndarray) and len(loaded_samples) > 1600:
            segments, info = model.transcribe(
                loaded_samples,
                beam_size=1,
                language="en",
                vad_filter=True,
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
