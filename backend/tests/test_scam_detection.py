from pathlib import Path
import pytest
from app.services.analysis import analyze_audio_file
from app.services.stt.social_engineering import analyze_context_detailed, infer_scam_category
from app.services.risk.scoring import calculate_risk_detailed


DEMO_GENUINE = Path(__file__).resolve().parent.parent.parent / "data" / "sample_audio" / "demo-genuine.wav"
DEMO_SYNTHETIC = Path(__file__).resolve().parent.parent.parent / "data" / "sample_audio" / "demo-synthetic.wav"


def test_silence_protection(tmp_path):
    import numpy as np, soundfile as sf
    silence_file = tmp_path / "silence.wav"
    waveform = np.zeros(16000 * 3, dtype=np.float32)
    sf.write(str(silence_file), waveform, 16000, format="WAV")

    result = analyze_audio_file(silence_file, transcript="Transfer money urgently right now.")
    assert result.analysis_status == "insufficient_audio"
    assert result.speech_detected is False
    assert result.final_risk_score is None
    assert result.risk_level == "NOT_ANALYZED"
    assert result.voice_authenticity == "NOT_ANALYZED"


def test_routine_conversation_context():
    transcript = "Good morning team, let us review the quarterly engineering roadmap before the sprint planning session."
    res = analyze_context_detailed(transcript)
    assert res["context_risk"] < 0.20
    assert res["possible_scam_category"] == "Routine / Normal Call"
    assert res["risk_level"] == "LOW"


def test_digital_arrest_extortion_context():
    transcript = "This is CBI Crime Branch. You are under digital arrest in a money laundering case. Do not tell anyone, stay on the line, and transfer 5 lakh rupees immediately."
    res = analyze_context_detailed(transcript)
    assert res["context_risk"] >= 0.70
    assert res["risk_level"] == "CRITICAL"
    assert "Digital Arrest" in res["possible_scam_category"]


def test_banking_kyc_and_otp_context():
    transcript = "Your bank account and debit card are blocked due to pending KYC verification. To unblock immediately, share the OTP sent to your mobile number."
    res = analyze_context_detailed(transcript)
    assert res["context_risk"] >= 0.50
    assert res["risk_level"] in {"HIGH", "CRITICAL"}
    assert ("Banking" in res["possible_scam_category"] or "OTP" in res["possible_scam_category"])


def test_customs_contraband_parcel_context():
    transcript = "Customs department calling regarding your FedEx courier parcel containing illegal contraband and drugs. Pay the clearance penalty amount immediately."
    res = analyze_context_detailed(transcript)
    assert res["context_risk"] >= 0.50
    assert ("Parcel" in res["possible_scam_category"] or "Customs" in res["possible_scam_category"])


def test_tech_support_remote_access_context():
    transcript = "Your Windows computer has a critical virus infection. Please download AnyDesk and share your screen to bypass security locks."
    res = analyze_context_detailed(transcript)
    assert "Tech Support" in res["possible_scam_category"]


def test_human_voice_does_not_dilute_severe_fraud():
    score, risk_level, rec, breakdown = calculate_risk_detailed(
        deepfake_probability=0.05,
        prosody_score=0.10,
        speaker_mismatch=0.0,
        context_risk=0.85,
        has_speaker_reference=False,
        detected_indicators=[
            {"category": "DIGITAL_ARREST_LEGAL_THREAT"},
            {"category": "FINANCIAL_REQUEST"},
            {"category": "SECRECY_COERCION"},
        ],
    )
    assert risk_level == "CRITICAL"
    assert score >= 90
    assert breakdown["escalation_applied"] is True


def test_ai_voice_clone_synergy_escalation():
    score, risk_level, rec, breakdown = calculate_risk_detailed(
        deepfake_probability=0.95,
        prosody_score=0.10,
        speaker_mismatch=0.0,
        context_risk=0.32,
        has_speaker_reference=False,
        detected_indicators=[
            {"category": "FINANCIAL_REQUEST"},
            {"category": "URGENCY_PRESSURE"},
        ],
    )
    assert risk_level == "CRITICAL"
    assert score >= 90
    assert breakdown["escalation_applied"] is True


def test_end_to_end_analysis_no_speaker_required():
    if not DEMO_GENUINE.exists():
        pytest.skip("Sample genuine audio not found")

    result = analyze_audio_file(
        DEMO_GENUINE,
        transcript="This is CBI officer. Digital arrest in narcotics case. Transfer money immediately.",
        reference_embedding=None,
    )
    assert result.analysis_status == "completed"
    assert result.speaker_match is None
    assert result.risk_level == "CRITICAL"
    assert result.final_risk_score >= 90
    assert "Digital Arrest" in result.possible_scam_category
