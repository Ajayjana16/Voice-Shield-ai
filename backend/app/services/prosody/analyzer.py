from app.models.schemas import AcousticFeatures


def prosody_anomaly_score(features: AcousticFeatures) -> tuple[float, list[str]]:
    """
    Evaluates acoustic prosody dynamics.
    Natural human speech exhibits pauses, breathing, and pitch inflection.
    This analyzer only flags extreme non-biological anomalies (e.g. completely flat monotone)
    when sufficient sustained audio (>= 4.0s) is present.
    """
    duration = features.duration_seconds or 0.0
    if duration < 4.0 or features.rms_energy < 0.0050:
        return 0.0, []

    score = 0.0
    reasons: list[str] = []

    # Extremely unnatural robotic monotone: zero dynamic range (< 0.02) combined with extreme pitch clamp
    if features.dynamic_range < 0.02 and (features.pitch_hz < 60 or features.pitch_hz > 450):
        score += 0.30
        reasons.append("Sustained flat robotic monotone with unnatural pitch limits.")

    return min(score, 1.0), reasons

