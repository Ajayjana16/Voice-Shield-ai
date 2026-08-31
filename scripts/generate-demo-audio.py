import math
import wave
from pathlib import Path


def write_synthetic_speech_sample(
    path: Path,
    carrier_freq: float = 160.0,
    seconds: float = 3.0,
    sample_rate: int = 16000,
    is_synthetic_vocoder: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(seconds * sample_rate)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        if is_synthetic_vocoder:
            # Synthetic vocoder artifacts:
            # Robotic flat harmonic series + high-frequency phase noise (ZCR > 0.32) + flat dynamic range (< 0.07)
            val = math.sin(2 * math.pi * carrier_freq * t) * 0.03
            val += math.sin(2 * math.pi * (carrier_freq * 2) * t) * 0.02
            val += (math.sin(i * 12.345) * 0.015)
            envelope = 0.95
        else:
            # Natural biological human voice:
            # Fundamental + natural vibrato/jitter + biological formants (F1, F2, F3) + smooth organic pauses
            f0 = carrier_freq + 4.0 * math.sin(2 * math.pi * 3.0 * t)
            val = math.sin(2 * math.pi * f0 * t) * 0.4
            val += math.sin(2 * math.pi * (f0 * 2) * t) * 0.2
            val += math.sin(2 * math.pi * (f0 * 3) * t) * 0.1
            envelope = math.sin(math.pi * (t / seconds)) * (0.8 + 0.2 * math.sin(2 * math.pi * 1.5 * t))

        sample_float = val * envelope
        sample_int = int(max(-1.0, min(1.0, sample_float)) * 32767)
        samples.append(sample_int)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(s.to_bytes(2, "little", signed=True) for s in samples))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sample_dir = root / "data" / "sample_audio"

    # 1. Registered Reference Voice (CEO Voice Reference)
    write_synthetic_speech_sample(sample_dir / "demo-reference.wav", carrier_freq=150.0, seconds=3.0, is_synthetic_vocoder=False)

    # 2. Genuine Human Call (Authentic Caller Matching Reference)
    write_synthetic_speech_sample(sample_dir / "demo-genuine.wav", carrier_freq=152.0, seconds=3.0, is_synthetic_vocoder=False)

    # 3. AI Cloned / Synthetic Speech Call (Vocoder Artifacts)
    write_synthetic_speech_sample(sample_dir / "demo-synthetic.wav", carrier_freq=150.0, seconds=3.0, is_synthetic_vocoder=True)

    # 4. Impostor Caller with Urgent Financial Coercion (Different Pitch & Impersonation)
    write_synthetic_speech_sample(sample_dir / "demo-call.wav", carrier_freq=240.0, seconds=3.0, is_synthetic_vocoder=False)

    print("Generated high-fidelity demo audio files:")
    print("  - data/sample_audio/demo-reference.wav (Registered Reference Voice)")
    print("  - data/sample_audio/demo-genuine.wav   (Scenario 1: Clean Genuine Voice)")
    print("  - data/sample_audio/demo-synthetic.wav (Scenario 2: AI-Cloned Synthetic Voice)")
    print("  - data/sample_audio/demo-call.wav      (Scenario 3: Impostor / Social Engineering Call)")

