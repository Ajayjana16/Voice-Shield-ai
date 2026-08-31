from app.services.stt.social_engineering import analyze_context


def test_detects_social_engineering_text() -> None:
    score, indicators = analyze_context("This is urgent. Transfer money now and do not tell anyone.")

    assert score > 0.5
    assert any("Urgency" in ind for ind in indicators)
    assert any("Financial" in ind for ind in indicators)
    assert any("Secrecy" in ind for ind in indicators)
