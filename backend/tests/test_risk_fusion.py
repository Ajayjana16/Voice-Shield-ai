from app.services.risk.scoring import calculate_risk, calculate_risk_detailed


def test_calculate_risk_detailed_breakdown():
    final_score, risk_level, recommendation, breakdown = calculate_risk_detailed(
        deepfake_probability=0.85,
        prosody_score=0.60,
        speaker_mismatch=0.75,
        context_risk=0.80,
        has_speaker_reference=True,
    )

    assert final_score >= 80
    assert risk_level == "CRITICAL"
    assert "points_breakdown" in breakdown
    assert "synthetic_voice_points" in breakdown["points_breakdown"]
    assert "speaker_mismatch_points" in breakdown["points_breakdown"]
    assert "dominant_driver" in breakdown
    assert "weights" in breakdown


def test_calculate_risk_without_speaker_reference():
    score_no_ref, level_no_ref, _, _ = calculate_risk_detailed(
        deepfake_probability=0.10,
        prosody_score=0.10,
        speaker_mismatch=0.0,
        context_risk=0.0,
        has_speaker_reference=False,
    )
    assert score_no_ref <= 15
    assert level_no_ref == "LOW"
