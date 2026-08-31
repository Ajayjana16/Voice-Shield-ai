from app.services.risk.scoring import calculate_risk


def test_calculate_critical_risk() -> None:
    score, level, recommendation = calculate_risk(0.95, 0.8, 0.9, 0.85)

    assert score >= 81
    assert level == "CRITICAL"
    assert "verification" in recommendation.lower()


def test_calculate_low_risk() -> None:
    score, level, _ = calculate_risk(0.05, 0.1, 0.0, 0.0)

    assert score <= 30
    assert level == "LOW"
