import hashlib
import math
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.schemas import AcousticFeatures

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    _HAS_NUMPY = False

try:
    import soundfile as sf
    _HAS_SOUNDFILE = True
except ImportError:
    sf = None  # type: ignore
    _HAS_SOUNDFILE = False

try:
    import scipy.signal as sp_signal
    _HAS_SCIPY = True
except ImportError:
    sp_signal = None  # type: ignore
    _HAS_SCIPY = False


@dataclass(frozen=True)
class AudioData:
    samples: list[float]
    sample_rate: int | None
    duration_seconds: float
    byte_entropy: float
    digest: str


def load_audio(path: Path | str) -> AudioData:
    path = Path(path)
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    entropy = _byte_entropy(data)

    # Strategy 1: soundfile (supports WAV, FLAC, OGG, AIFF, etc.)
    if _HAS_SOUNDFILE and sf is not None:
        try:
            audio_arr, sr = sf.read(str(path), dtype="float32")
            if audio_arr.ndim > 1:
                audio_arr = np.mean(audio_arr, axis=1)
            samples = audio_arr.tolist()
            duration = len(samples) / sr if sr else 0.0
            return AudioData(samples, int(sr), duration, entropy, digest)
        except Exception:
            pass

    # Strategy 2: standard library wave module (PCM WAV)
    try:
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            channels = wav.getnchannels()
            frames = wav.readframes(wav.getnframes())
            samples = _pcm_to_float(frames, sample_width, channels)
            duration = len(samples) / sample_rate if sample_rate else 0.0
            return AudioData(samples, sample_rate, duration, entropy, digest)
    except (wave.Error, EOFError):
        pass

    # Strategy 3: byte stream fallback signal
    pseudo_samples = _bytes_to_signal(data)
    duration = max(len(data) / 16000.0, 0.1)
    return AudioData(pseudo_samples, None, duration, entropy, digest)


def load_audio_resampled(path: Path, target_sr: int = 16000) -> tuple[Any, int]:
    """
    Loads audio from path as a 1D float32 numpy array resampled to target_sr (default 16000Hz).
    Returns (samples_array, sample_rate).
    """
    audio = load_audio(path)
    sr = audio.sample_rate or 16000
    samples = audio.samples

    if _HAS_NUMPY and np is not None:
        arr = np.array(samples, dtype=np.float32)
        if len(arr) == 0:
            return np.zeros(target_sr, dtype=np.float32), target_sr

        if sr != target_sr:
            if _HAS_SCIPY and sp_signal is not None:
                num_target_samples = int(len(arr) * target_sr / sr)
                arr = sp_signal.resample(arr, num_target_samples).astype(np.float32)
            else:
                orig_indices = np.linspace(0, len(arr) - 1, len(arr))
                num_target_samples = int(len(arr) * target_sr / sr)
                new_indices = np.linspace(0, len(arr) - 1, num_target_samples)
                arr = np.interp(new_indices, orig_indices, arr).astype(np.float32)

        # Normalize peak amplitude if necessary
        max_val = float(np.max(np.abs(arr))) if len(arr) > 0 else 0.0
        if max_val > 1.0:
            arr = arr / max_val
        return arr, target_sr

    return samples, sr


def validate_speech_activity(
    samples: list[float] | Any,
    sample_rate: int = 16000,
    min_duration_sec: float = 0.40,
    min_voiced_duration_sec: float = 0.20,
) -> tuple[bool, str, float]:
    """
    Audio Validation & Speech Activity Gate (VAD).
    Determines if audio contains sufficient audible voiced human speech for trustworthy analysis.

    Checks:
    1. Duration >= min_duration_sec
    2. Peak amplitude >= 0.015 (filters absolute silence & quantization noise)
    3. RMS energy >= 0.0030 (filters dead air / background hiss)
    4. Voiced speech frame accumulation (energy and zero-crossing analysis)

    Returns: (is_valid_speech: bool, failure_or_success_reason: str, voiced_duration_sec: float)
    """
    if not _HAS_NUMPY or np is None or not isinstance(samples, np.ndarray):
        arr = np.array(samples, dtype=np.float32) if _HAS_NUMPY and np is not None else samples
    else:
        arr = samples

    if len(arr) == 0:
        return False, "Audio stream is empty (0 samples).", 0.0

    duration = len(arr) / float(sample_rate)
    if duration < min_duration_sec:
        return False, f"Audio duration too short ({duration:.2f}s < {min_duration_sec:.2f}s).", 0.0

    if _HAS_NUMPY and np is not None and isinstance(arr, np.ndarray):
        peak = float(np.max(np.abs(arr)))
        if peak < 0.015:
            return False, "Audio is silent or peak amplitude is below audible threshold (<0.015).", 0.0

        rms = float(np.sqrt(np.mean(arr ** 2)))
        if rms < 0.0030:
            return False, f"RMS energy below speech floor ({rms:.5f} < 0.00300).", 0.0

        # Frame-level voiced analysis (25ms frame, 10ms hop)
        frame_len = int(0.025 * sample_rate)
        frame_step = int(0.010 * sample_rate)
        num_frames = (len(arr) - frame_len) // frame_step

        if num_frames <= 0:
            return False, "Audio too short for acoustic frame evaluation.", 0.0

        energy_threshold = max(0.0055, rms * 0.35)
        voiced_frames = 0

        for i in range(num_frames):
            start = i * frame_step
            frame = arr[start : start + frame_len]
            frame_rms = float(np.sqrt(np.mean(frame ** 2)))

            # Zero-crossing rate within frame
            diff_signs = np.diff(np.signbit(frame))
            zcr = float(np.mean(diff_signs))

            # Voiced human speech typically has moderate ZCR (<0.55) and frame energy > threshold
            if frame_rms >= energy_threshold and zcr < 0.55:
                voiced_frames += 1

        voiced_duration = (voiced_frames * frame_step) / float(sample_rate)
        if voiced_duration < min_voiced_duration_sec:
            return False, f"Insufficient voiced speech detected ({voiced_duration:.2f}s < {min_voiced_duration_sec:.2f}s required).", voiced_duration

        return True, "Sufficient speech detected for reliable multi-signal analysis.", voiced_duration

    # Pure Python list fallback
    peak = max(abs(s) for s in arr) if arr else 0.0
    if peak < 0.015:
        return False, "Audio is silent (<0.015 peak).", 0.0
    rms = math.sqrt(sum(s * s for s in arr) / len(arr))
    if rms < 0.0030:
        return False, "RMS energy below speech floor.", 0.0
    return True, "Speech activity detected.", duration


def slice_into_chunks(
    samples: list[float] | Any,
    sample_rate: int = 16000,
    chunk_duration_sec: float = 3.0,
    overlap_sec: float = 1.0,
) -> list[Any]:
    chunk_size = int(chunk_duration_sec * sample_rate)
    step_size = int((chunk_duration_sec - overlap_sec) * sample_rate)
    step_size = max(step_size, 1)

    if _HAS_NUMPY and np is not None and isinstance(samples, np.ndarray):
        if len(samples) <= chunk_size:
            return [samples]
        chunks = []
        for start in range(0, len(samples) - chunk_size // 2, step_size):
            end = min(start + chunk_size, len(samples))
            chunk = samples[start:end]
            if len(chunk) < chunk_size:
                pad_width = chunk_size - len(chunk)
                chunk = np.pad(chunk, (0, pad_width), mode="constant")
            chunks.append(chunk)
        return chunks

    if len(samples) <= chunk_size:
        return [samples]
    chunks_list = []
    for start in range(0, len(samples) - chunk_size // 2, step_size):
        end = min(start + chunk_size, len(samples))
        chunk = samples[start:end]
        if len(chunk) < chunk_size:
            chunk = chunk + [0.0] * (chunk_size - len(chunk))
        chunks_list.append(chunk)
    return chunks_list


def extract_features(audio: AudioData) -> AcousticFeatures:
    samples = audio.samples
    if not samples:
        return AcousticFeatures(
            duration_seconds=0,
            sample_rate=audio.sample_rate,
            rms_energy=0,
            zero_crossing_rate=0,
            spectral_centroid=0,
            spectral_contrast=0,
            pitch_hz=0,
            pause_ratio=1,
            dynamic_range=0,
            byte_entropy=audio.byte_entropy,
        )

    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    zero_crossing_rate = _zero_crossing_rate(samples)
    centroid = _spectral_centroid(samples, audio.sample_rate or 16000)
    contrast = _dynamic_contrast(samples)
    pitch = _estimate_pitch(samples, audio.sample_rate or 16000)
    pause_ratio = _pause_ratio(samples)
    dynamic_range = max(samples) - min(samples)

    return AcousticFeatures(
        duration_seconds=round(audio.duration_seconds, 3),
        sample_rate=audio.sample_rate,
        rms_energy=round(rms, 5),
        zero_crossing_rate=round(zero_crossing_rate, 5),
        spectral_centroid=round(centroid, 2),
        spectral_contrast=round(contrast, 5),
        pitch_hz=round(pitch, 2),
        pause_ratio=round(pause_ratio, 5),
        dynamic_range=round(dynamic_range, 5),
        byte_entropy=round(audio.byte_entropy, 5),
    )


def _pcm_to_float(frames: bytes, sample_width: int, channels: int) -> list[float]:
    if sample_width == 1:
        values = [(byte - 128) / 128 for byte in frames]
        return _mix_channels(values, channels)
    if sample_width == 2:
        values = array("h")
        values.frombytes(frames)
        return _mix_channels([value / 32768 for value in values], channels)
    if sample_width == 4:
        values = array("i")
        values.frombytes(frames)
        return _mix_channels([value / 2147483648 for value in values], channels)
    return _bytes_to_signal(frames)


def _mix_channels(values: list[float], channels: int) -> list[float]:
    if channels <= 1:
        return values
    mixed: list[float] = []
    for start in range(0, len(values), channels):
        frame = values[start : start + channels]
        if frame:
            mixed.append(sum(frame) / len(frame))
    return mixed


def _bytes_to_signal(data: bytes) -> list[float]:
    if not data:
        return []
    step = max(len(data) // 8000, 1)
    return [((data[index] - 128) / 128) for index in range(0, len(data), step)]


def _byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    entropy = 0.0
    for count in counts:
        if count:
            probability = count / len(data)
            entropy -= probability * math.log2(probability)
    return entropy / 8


def _zero_crossing_rate(samples: list[float]) -> float:
    crossings = 0
    for index in range(1, len(samples)):
        if (samples[index - 1] >= 0) != (samples[index] >= 0):
            crossings += 1
    return crossings / max(len(samples) - 1, 1)


def _spectral_centroid(samples: list[float], sample_rate: int) -> float:
    window = samples[: min(len(samples), 4096)]
    if len(window) < 2:
        return 0.0
    magnitudes = []
    for frequency_bin in range(1, min(256, len(window) // 2)):
        real = 0.0
        imaginary = 0.0
        for index, sample in enumerate(window):
            angle = 2 * math.pi * frequency_bin * index / len(window)
            real += sample * math.cos(angle)
            imaginary -= sample * math.sin(angle)
        magnitudes.append((frequency_bin, math.sqrt(real * real + imaginary * imaginary)))
    total = sum(magnitude for _, magnitude in magnitudes)
    if total == 0:
        return 0.0
    weighted = sum(bin_index * magnitude for bin_index, magnitude in magnitudes)
    return (weighted / total) * sample_rate / len(window)


def _dynamic_contrast(samples: list[float]) -> float:
    chunk_size = max(len(samples) // 20, 1)
    energies = []
    for start in range(0, len(samples), chunk_size):
        chunk = samples[start : start + chunk_size]
        if chunk:
            energies.append(math.sqrt(sum(sample * sample for sample in chunk) / len(chunk)))
    if not energies:
        return 0.0
    return max(energies) - min(energies)


def _estimate_pitch(samples: list[float], sample_rate: int) -> float:
    if len(samples) < sample_rate // 20:
        return 0.0
    min_lag = max(sample_rate // 400, 1)
    max_lag = max(sample_rate // 70, min_lag + 1)
    segment = samples[: min(len(samples), sample_rate)]
    best_lag = 0
    best_score = 0.0
    for lag in range(min_lag, min(max_lag, len(segment) // 2)):
        score = 0.0
        for index in range(len(segment) - lag):
            score += segment[index] * segment[index + lag]
        if score > best_score:
            best_score = score
            best_lag = lag
    return sample_rate / best_lag if best_lag else 0.0


def _pause_ratio(samples: list[float]) -> float:
    if not samples:
        return 1.0
    threshold = max(0.015, math.sqrt(sum(sample * sample for sample in samples) / len(samples)) * 0.25)
    quiet = sum(1 for sample in samples if abs(sample) < threshold)
    return quiet / len(samples)
