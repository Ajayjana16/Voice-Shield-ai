from app.services.stt.social_engineering import analyze_context, analyze_context_detailed


def test_english_coercion_cues():
    res = analyze_context_detailed("This is urgent. Transfer funds to this account number and keep this strictly confidential.")
    assert res["context_risk"] >= 0.60
    assert res["risk_level"] in {"HIGH", "CRITICAL"}
    assert "English" in res["language"]
    categories = {item.category for item in res["detected_indicators"]}
    assert "FINANCIAL_REQUEST" in categories
    assert "SECRECY_COERCION" in categories
    assert "URGENCY_PRESSURE" in categories


def test_hinglish_and_hindi_fraud_cues():
    # Hinglish urgent transfer + OTP extortion
    res = analyze_context_detailed("Turant paise bhejo khate me, aur OTP kisi ko mat batana, police case ban jayega.")
    assert res["context_risk"] >= 0.70
    assert res["risk_level"] in {"HIGH", "CRITICAL"}
    categories = {item.category for item in res["detected_indicators"]}
    assert "FINANCIAL_REQUEST" in categories
    assert "CREDENTIAL_OTP" in categories or "SECRECY_COERCION" in categories

    # Devanagari Hindi
    res_hi = analyze_context_detailed("तुरंत पैसे ट्रांसफर करो और अपना ओटीपी शेयर करो")
    assert res_hi["context_risk"] >= 0.50
    assert "Hindi" in res_hi["language"]


def test_south_indian_language_cues():
    # Telugu
    res_te = analyze_context_detailed("Ventane dabbu pampandi, evariki cheppavaddhu, idi rahasyam.")
    assert res_te["context_risk"] >= 0.50
    assert "Telugu" in res_te["language"]

    # Tamil
    res_ta = analyze_context_detailed("Udane panam anuppu, yaarukkum sollaatheenga, ragasiyam.")
    assert res_ta["context_risk"] >= 0.50
    assert "Tamil" in res_ta["language"]


def test_safe_conversational_negatives():
    # Routine business and casual conversation should not trigger false alarms
    safe_samples = [
        "Hello everyone, let's discuss the project milestones for the next sprint.",
        "Good morning, please review the attached slide deck when you get a chance.",
        "Thank you for attending the hackathon demonstration today.",
        "Can we reschedule our sync to tomorrow afternoon at 3 PM?",
    ]
    for sample in safe_samples:
        score, indicators = analyze_context(sample)
        assert score == 0.0
        assert len(indicators) == 0

