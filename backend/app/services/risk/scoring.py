from typing import Any

from app.core.config import get_settings


def calculate_risk_detailed(
    deepfake_probability: float,
    prosody_score: float,
    speaker_mismatch: float,
    context_risk: float | None,
    has_speaker_reference: bool = False,
    detected_indicators: list[Any] | None = None,
    has_transcript: bool = True,
) -> tuple[int, str, str, dict[str, Any]]:
    """
    Computes a calibrated multi-signal risk score with strict logical consistency
    and security-aware escalation rules.
    """
    settings = get_settings()

    # If transcript is missing, calculate acoustic-only score and mark as partial
    if not has_transcript or context_risk is None:
        effective_context = 0.0
        w_deepfake = 0.65
        w_prosody = 0.35
        w_speaker = 0.0
        w_context = 0.0
    else:
        effective_context = context_risk
        if has_speaker_reference:
            w_deepfake = settings.deepfake_weight
            w_speaker = settings.speaker_weight
            w_prosody = settings.prosody_weight
            w_context = settings.context_weight
        else:
            w_deepfake = 0.40
            w_speaker = 0.00
            w_prosody = 0.15
            w_context = 0.45

    effective_mismatch = speaker_mismatch if has_speaker_reference else 0.0

    adjusted_prosody = prosody_score
    if deepfake_probability > 0.60 and prosody_score > 0.40:
        adjusted_prosody = prosody_score * 0.80

    raw_weighted = (
        w_deepfake * deepfake_probability
        + w_prosody * adjusted_prosody
        + w_speaker * effective_mismatch
        + w_context * effective_context
    )

    base_score = round(raw_weighted * 100)
    escalated_score = base_score
    escalation_reasons: list[str] = []

    categories_found: set[str] = set()
    severities_found: set[str] = set()
    indicator_cues: list[str] = []

    if detected_indicators:
        for ind in detected_indicators:
            cat = getattr(ind, "category", "") or (ind.get("category", "") if isinstance(ind, dict) else "")
            sev = getattr(ind, "severity", "") or (ind.get("severity", "") if isinstance(ind, dict) else "")
            cue = getattr(ind, "matched_cue", "") or (ind.get("matched_cue", "") if isinstance(ind, dict) else "")
            lbl = getattr(ind, "label", "") or (ind.get("label", "") if isinstance(ind, dict) else "")

            if cat:
                categories_found.add(cat)
            if sev:
                severities_found.add(sev)
            if cue and lbl:
                indicator_cues.append(f"{lbl} (evidence: \"{cue}\")")
            elif lbl:
                indicator_cues.append(lbl)

    effective_mismatch = speaker_mismatch if has_speaker_reference else 0.0

    # ---------------------------------------------------------
    # 1. CONVERSATION THREAT EVIDENCE (0–70 points maximum)
    # ---------------------------------------------------------
    has_otp = "CREDENTIAL_OTP" in categories_found
    has_arrest = "DIGITAL_ARREST_LEGAL_THREAT" in categories_found
    has_finance = "FINANCIAL_REQUEST" in categories_found
    has_authority = "AUTHORITY_IMPERSONATION" in categories_found
    has_urgency = "URGENCY_PRESSURE" in categories_found
    has_secrecy = "SECRECY_COERCION" in categories_found
    has_bank = "BANK_FRAUD_UNAUTHORIZED" in categories_found
    has_parcel = "PARCEL_CUSTOMS_SCAM" in categories_found
    has_investment = "INVESTMENT_JOB_SCAM" in categories_found
    has_blackmail = "BLACKMAIL_EXTORTION" in categories_found

    if not has_transcript or context_risk is None:
        conv_pts = 0.0
    elif not categories_found:
        if effective_context > 0.20:
            conv_pts = round(effective_context * 70.0, 1)
        else:
            conv_pts = 5.0 if (has_transcript and effective_context > 0.0) else (effective_context * 70.0)

    elif has_otp:
        conv_pts = 70.0 if (has_urgency or has_finance or has_authority or has_secrecy or has_bank) else 65.0
    elif has_arrest:
        conv_pts = 70.0 if (has_finance or has_urgency or has_secrecy) else 65.0
    elif has_blackmail:
        conv_pts = 70.0 if has_finance else 65.0
    elif has_investment:
        conv_pts = 65.0
    elif has_finance and (has_urgency or has_bank or has_authority or has_secrecy):
        conv_pts = 60.0
    elif has_bank and has_urgency:
        conv_pts = 60.0
    elif has_parcel and has_finance:
        conv_pts = 60.0
    elif has_finance or has_bank or has_parcel:
        conv_pts = 45.0
    elif has_authority:
        conv_pts = 45.0 if has_secrecy else 35.0
    elif has_urgency or has_secrecy:
        # Check repeated urgency
        urgency_cues = [ind for ind in (detected_indicators or []) if getattr(ind, "category", "") == "URGENCY_PRESSURE"]
        conv_pts = 35.0 if len(urgency_cues) >= 2 else 25.0
    else:
        conv_pts = 20.0

    # ---------------------------------------------------------
    # 2. VOICE AUTHENTICITY RISK (0–15 points maximum)
    # ---------------------------------------------------------
    # Synthetic suspicion alone should never generate critical risk.
    # Inconclusive / low confidence contributes 0 points.
    if deepfake_probability >= 0.85:
        voice_pts = 15.0
    elif deepfake_probability >= 0.70:
        voice_pts = 8.0
    else:
        voice_pts = 0.0

    # ---------------------------------------------------------
    # 3. BEHAVIORAL / CONTEXTUAL SIGNALS (0–15 points maximum)
    # ---------------------------------------------------------
    context_pts = 0.0
    if len(categories_found) >= 3 or (has_otp and (has_urgency or has_finance)) or (has_arrest and has_finance):
        context_pts = 15.0
    elif len(categories_found) == 2:
        context_pts = 10.0
    elif len(categories_found) == 1:
        context_pts = 5.0
    elif effective_context >= 0.70:
        context_pts = 15.0
    elif effective_context >= 0.40:
        context_pts = 8.0

    if has_speaker_reference and effective_mismatch >= 0.35:
        spk_bonus = round(effective_mismatch * 15.0, 1)
        context_pts = min(15.0, context_pts + spk_bonus)

    # ---------------------------------------------------------
    # TOTAL SCORE & CONSISTENCY ENFORCEMENT
    # ---------------------------------------------------------
    if not has_transcript or context_risk is None:
        # Partial acoustic analysis: max 70 from acoustic + 30 from speaker
        raw_score = round(deepfake_probability * 70.0 + (effective_mismatch * 30.0 if has_speaker_reference else 0.0))
        final_score = max(0, min(100, raw_score))
        risk_level = "PARTIAL_ANALYSIS"
        recommendation = "PARTIAL ANALYSIS: Voice audio was evaluated acoustically, but spoken conversation content was not available. If caller is asking for OTPs, passwords, or urgent funds, treat as high risk."
        dominant_driver = "Acoustic Audio"
        risk_reasoning = "Spoken conversation was not available for scam intent analysis. Acoustic signals evaluated."
    else:
        raw_score = round(conv_pts + voice_pts + context_pts)

        # STRICT CONSISTENCY RULE 1: Credential / OTP Request
        if has_otp:
            min_otp_score = 85 if (has_finance or has_urgency) else 80
            raw_score = max(raw_score, min_otp_score)

        # STRICT CONSISTENCY RULE 2: Digital Arrest or severe extortion
        if has_arrest and (has_finance or has_urgency or has_secrecy):
            raw_score = max(raw_score, 90)

        # STRICT CONSISTENCY RULE 3: AI Voice Clone + Fraud Intent Synergy
        if deepfake_probability >= 0.85 and (has_finance or has_otp or has_arrest or has_urgency):
            raw_score = max(raw_score, 90)

        # STRICT CONSISTENCY RULE 4: Severe fraud indicators in transcript
        if "CRITICAL" in severities_found and raw_score < 80:
            raw_score = max(raw_score, 80)

        # STRICT CONSISTENCY RULE 5: Routine / Normal Call
        # If no threat indicators exist and context risk is baseline, risk CANNOT be High or Critical!
        if not categories_found and effective_context <= 0.20:
            if deepfake_probability >= 0.75:
                raw_score = min(raw_score, 25)
            else:
                raw_score = min(raw_score, 15)

        # STRICT CONSISTENCY RULE 6: Synthetic voice suspicion alone
        # Cannot produce CRITICAL risk without active fraud cues
        if not categories_found and effective_context <= 0.20 and raw_score > 25:
            raw_score = 25

        final_score = max(0, min(100, raw_score))

        # Risk level determination
        if final_score >= 75 and (categories_found or not has_transcript or effective_context >= 0.50 or deepfake_probability >= 0.60):
            risk_level = "CRITICAL"
            if has_arrest or (has_authority and has_finance):
                recommendation = "CRITICAL THREAT: Disconnect the call immediately. Do not transfer funds. Perform secondary verification with official police or government contacts directly."
            elif has_otp:
                recommendation = "CRITICAL THREAT: Never share OTPs, passwords, or card PINs. Disconnect immediately and perform secondary verification with your bank."
            else:
                recommendation = "CRITICAL THREAT: Severe fraud or extortion indicators detected. Do not comply with demands. Perform secondary verification independently."

        elif final_score >= 50:
            risk_level = "HIGH"
            if has_otp:
                recommendation = "HIGH RISK: Request for sensitive OTP or verification codes detected. Never disclose authentication codes over phone calls."
            elif has_finance:
                recommendation = "HIGH RISK: Urgent financial demands detected. Verify caller identity independently before taking action."
            else:
                recommendation = "HIGH RISK: Strong indicators of telecommunication fraud or impersonation. Exercise caution and verify caller identity."
        elif final_score >= 25:
            risk_level = "MODERATE"
            recommendation = "MODERATE RISK: Unverified caller claims, pressure tactics, or unusual conversational cues detected. Proceed with caution."
        else:
            risk_level = "LOW"
            recommendation = "LOW RISK: No high-confidence scam indicators or synthetic voice artifacts identified in the evaluated content."

        # Dominant driver
        if conv_pts >= voice_pts and conv_pts >= context_pts and conv_pts > 0:
            dominant_driver = "Conversation Threat Evidence"
        elif voice_pts > conv_pts and voice_pts > 0:
            dominant_driver = "Synthetic Voice Authenticity"
        elif final_score <= 20:
            dominant_driver = "Routine Speech"
        else:
            dominant_driver = "Multi-Signal Context"

        if has_otp:
            risk_reasoning = f"Direct request for authentication credentials / OTP detected ({final_score}/100)."
        elif has_arrest:
            risk_reasoning = f"Coercive authority claims or digital arrest threats detected ({final_score}/100)."
        elif has_finance and has_urgency:
            risk_reasoning = f"High-pressure financial transfer demands detected ({final_score}/100)."
        elif final_score >= 46:
            risk_reasoning = f"Analysis identified {dominant_driver} as primary threat signal ({final_score}/100)."
        elif final_score >= 21:
            risk_reasoning = "Moderate conversational or acoustic cues detected. Secondary verification recommended."
        else:
            risk_reasoning = "Baseline conversation and acoustic parameters match standard human speech."

    points_breakdown = {
        "conversation_threat_points": conv_pts,
        "voice_authenticity_points": voice_pts,
        "behavioral_context_points": context_pts,
        "synthetic_voice_points": voice_pts,
        "speaker_points": round(effective_mismatch * 15.0, 1),
        "speaker_mismatch_points": round(effective_mismatch * 15.0, 1),
        "context_points": conv_pts,
        "context_risk_points": conv_pts,
        "prosody_points": 0.0,
    }

    breakdown = {
        "formula": "conversation_threat (0-70) + voice_authenticity (0-15) + contextual_signals (0-15)",
        "weights": {
            "conversation_max": 70,
            "voice_authenticity_max": 15,
            "contextual_max": 15,
            "deepfake": w_deepfake,
            "prosody": w_prosody,
            "speaker": w_speaker,
            "context": w_context,
        },
        "contributions": {
            "Conversation Threat Evidence": conv_pts,
            "Voice Authenticity Signal": voice_pts,
            "Contextual & Biometric Signals": context_pts,
            "Synthetic Voice Artifacts": voice_pts,
            "Conversation Fraud Intent": conv_pts,
            "Prosody Anomaly": 0.0,
            "Speaker Biometric Mismatch": round(effective_mismatch * 15.0, 1),
        },
        "points_breakdown": points_breakdown,
        "dominant_driver": dominant_driver,
        "base_score": final_score,
        "escalated_score": final_score,
        "escalation_applied": bool(
            final_score >= 80
            or has_otp
            or has_arrest
            or (deepfake_probability >= 0.85 and (has_finance or has_urgency))
            or (effective_context >= 0.70)
        ),
        "escalation_reasons": indicator_cues if indicator_cues else (["Threat escalation applied based on high-confidence fraud cues."] if final_score >= 80 else []),
        "evidence_list": indicator_cues,
        "risk_reasoning": risk_reasoning,
    }

    return final_score, risk_level, recommendation, breakdown


def calculate_risk(
    deepfake_probability: float,
    prosody_score: float,
    speaker_mismatch: float,
    context_risk: float = 0.0,
    has_speaker_reference: bool = False,
) -> tuple[int, str, str]:
    score, level, rec, _ = calculate_risk_detailed(
        deepfake_probability=deepfake_probability,
        prosody_score=prosody_score,
        speaker_mismatch=speaker_mismatch,
        context_risk=context_risk,
        has_speaker_reference=has_speaker_reference,
    )
    return score, level, rec
