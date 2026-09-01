from app.models.schemas import AcousticFeatures


def prosody_anomaly_score(features: AcousticFeatures) -> tuple[float, list[str]]:
    """
    Evaluates acoustic prosody dynamics.
    Natural human speech exhibits pauses, breathing, and pitch inflection.
    """
    duration = features.duration_seconds or 0.0
    if duration < 2.0 or features.rms_energy < 0.0030:
        return 0.0, []

    score = 0.0
    reasons: list[str] = []

    # 1. Unnatural dynamic range compression (< 0.15)
    if features.dynamic_range < 0.15 and features.rms_energy > 0.01:
        score += 0.25
        reasons.append("Sustained flat dynamic amplitude envelope lacking natural syllabic modulation.")

    # 2. Extreme pitch clamp (< 65Hz or > 400Hz)
    if features.pitch_hz > 0 and (features.pitch_hz < 65 or features.pitch_hz > 400):
        score += 0.20
        reasons.append(f"Fundamental frequency ({features.pitch_hz:.1f}Hz) outside standard biological speech registers.")

    return min(score, 1.0), reasons

