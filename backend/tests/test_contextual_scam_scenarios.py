from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_scenario_a_normal_conversation():
    text = "hello good morning how are you doing today I am calling to discuss our project meeting tomorrow"
    resp = client.post("/api/context/analyze", json={"transcript": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_risk_score"] <= 15
    assert data["final_threat_level"] == "LOW"
    assert data["possible_scam_category"] == "Routine / Normal Call"
    assert data["scam_category_confidence"] == "HIGH"
    assert len(data["detected_indicators"]) == 0


def test_scenario_b_defensive_warning_not_flagged():
    text = "Do not share your OTP with anyone my bank sent me an OTP but I received an OTP for my login and you must never give your OTP"
    resp = client.post("/api/context/analyze", json={"transcript": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_risk_score"] <= 15
    assert data["final_threat_level"] == "LOW"
    assert data["possible_scam_category"] == "Routine / Normal Call"
    categories = [ind["category"] for ind in data["detected_indicators"]]
    assert "CREDENTIAL_OTP" not in categories


def test_scenario_c_scammer_requests_otp_urgently():
    text = "Tell me the OTP immediately I need the verification code right now"
    resp = client.post("/api/context/analyze", json={"transcript": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_risk_score"] >= 80
    assert data["final_threat_level"] == "CRITICAL"
    assert "OTP" in data["possible_scam_category"]
    assert data["scam_category_confidence"] == "HIGH"
    categories = [ind["category"] for ind in data["detected_indicators"]]
    assert "CREDENTIAL_OTP" in categories
    assert "URGENCY_PRESSURE" in categories


def test_scenario_d_scammer_asks_for_cvv_or_password():
    text = "Give me your CVV number and share your bank password now"
    resp = client.post("/api/context/analyze", json={"transcript": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_risk_score"] >= 80
    assert data["final_threat_level"] == "CRITICAL"
    assert "OTP" in data["possible_scam_category"]
    categories = [ind["category"] for ind in data["detected_indicators"]]
    assert "CREDENTIAL_OTP" in categories


def test_scenario_e_transfer_money_urgently_or_blocked():
    text = "Transfer money urgently or your account will be blocked"
    resp = client.post("/api/context/analyze", json={"transcript": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_risk_score"] >= 70
    categories = [ind["category"] for ind in data["detected_indicators"]]
    assert "FINANCIAL_REQUEST" in categories
    assert "BANK_FRAUD_UNAUTHORIZED" in categories
    assert "URGENCY_PRESSURE" in categories


def test_scenario_f_very_short_speech():
    text = "hello"
    resp = client.post("/api/context/analyze", json={"transcript": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_risk_score"] == 0
    assert data["final_threat_level"] == "Evaluating"
    assert data["possible_scam_category"] == "Listening for speech..."
    assert data["scam_category_confidence"] == "LOW"
