import logging
from typing import Any

from app.models.schemas import (
    AcousticFeatures,
    DetectedContextIndicator,
    SyntheticVoiceEvidence,
    ThreatIndicator,
    UnifiedDecisionPayload,
    VoiceAuthenticityDetail,
)
from app.services.detection.deepfake import DeepfakeDetectionResult

logger = logging.getLogger("voiceshield.decision_engine")


def evaluate_centralized_security_decision(
    df_result: DeepfakeDetectionResult,
    features: AcousticFeatures,
    transcript: str | None,
    detected_scam_indicators: list[DetectedContextIndicator],
    context_risk: float | None,
    prosody_score: float,
    speaker_mismatch: float,
    has_speaker_ref: bool,
    is_chunk: bool = False,
) -> dict[str, Any]:
    """
    ONE CENTRALIZED FINAL DECISION ENGINE
    Acts as the single source of truth for the entire Voice Shield analysis report.
    Guarantees strict logical consistency across:
      - Voice Authenticity & Anti-Spoofing
      - Possible Scam Category
      - Threat Indicators
      - Overall Threat Score & Risk Level
      - Recommended Action & Risk Reasoning
    """
    synth_p = float(df_result.synthetic_probability)
    human_prob = float(df_result.real_probability)
    duration = float(features.duration_seconds or 0.0)

    # =========================================================================
    # STEP 1: VOICE AUTHENTICITY DETERMINATION (DETERMINED FIRST)
    # =========================================================================
    if df_result.model_inference_skipped or df_result.prediction == "NOT_ANALYZED":
        voice_auth_label = "Voice authenticity analysis unavailable"
        auth_status = "skipped" if df_result.model_inference_skipped else "failed"
        auth_conf = "UNCERTAIN"
        is_synthetic = False
    elif df_result.prediction == "SYNTHETIC" or synth_p >= 0.70:
        voice_auth_label = "Likely Synthetic / AI Generated"
        auth_status = "completed"
        auth_conf = "HIGH" if synth_p >= 0.85 else "MEDIUM"
        is_synthetic = True
    elif synth_p >= 0.35 or df_result.prediction == "INCONCLUSIVE" or duration < 1.0 or is_chunk:
        voice_auth_label = "Uncertain"
        auth_status = "completed"
        auth_conf = "UNCERTAIN"
        is_synthetic = False
    else:
        voice_auth_label = "Likely Human"
        auth_status = "completed"
        auth_conf = "HIGH" if human_prob >= 0.85 else "MEDIUM"
        is_synthetic = False

    # =========================================================================
    # STEP 2: THREAT INDICATORS ASSEMBLY (STRICT SYNCHRONIZATION)
    # =========================================================================
    indicators: list[ThreatIndicator] = []

    # If synthetic, always attach the synthetic artifact indicator
    if is_synthetic and not is_chunk:
        severity = "CRITICAL" if synth_p >= 0.95 else ("HIGH" if synth_p >= 0.85 else "MEDIUM")
        indicators.append(
            ThreatIndicator(
                label="Synthetic / Cloned Voice Artifact",
                severity=severity,
                detail=f"Forensic acoustic classifier detected synthetic speech signatures ({round(synth_p * 100)}% synthetic probability).",
                explanation="Acoustic analysis detected unnatural spectral flatness, vocoder carrier filter artifacts, or synthetic phase modulation.",
                why_it_matters="Synthetic speech signals generative AI voice cloning commonly used in impersonation scams.",
            )
        )
    elif synth_p >= 0.50 and not is_chunk and duration >= 2.0:
        indicators.append(
            ThreatIndicator(
                label="Suspicious Voice Modulation",
                severity="LOW",
                detail=f"Acoustic characteristics exhibit elevated synthetic/vocoder traits ({round(synth_p * 100)}%).",
                explanation="Constrained pitch dynamics or unnatural spectral flatness observed in voice phonation.",
                why_it_matters="Potential use of voice conversion software or low-bitrate generative speech synthesis.",
            )
        )

    for item in detected_scam_indicators:
        matched_str = f"Evidence: \"{item.matched_cue}\"" if item.matched_cue else ""
        indicators.append(
            ThreatIndicator(
                label=item.label,
                severity=item.severity,
                detail=matched_str or item.category,
                explanation=item.explanation,
                why_it_matters=item.why_it_matters,
            )
        )

    detected_threat_labels = [
        ind.label for ind in indicators if ind.severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    ]

    # =========================================================================
    # STEP 3: SCAM CATEGORY INFERENCE (BOUND TO CENTRAL DECISION)
    # =========================================================================
    categories_found = {ind.category for ind in detected_scam_indicators}
    has_transcript = bool(transcript and transcript.strip())
    word_count = len(transcript.strip().split()) if has_transcript else 0

    if "PARCEL_CUSTOMS_SCAM" in categories_found:
        scam_cat = "Customs / Courier Parcel Extortion Scam"
        scam_conf = "HIGH" if word_count >= 4 else "MEDIUM"
        scam_desc = "The caller claims an intercepted package or contraband to demand clearance fees or impose extortion."
    elif "CREDENTIAL_OTP" in categories_found:
        scam_cat = "OTP & Credential Theft Attempt"
        scam_conf = "HIGH"
        scam_desc = "The conversation directly solicits one-time passwords, netbanking pins, or verification credentials."
    elif "DIGITAL_ARREST_LEGAL_THREAT" in categories_found or (
        "AUTHORITY_IMPERSONATION" in categories_found and ("SECRECY_COERCION" in categories_found or "FINANCIAL_REQUEST" in categories_found)
    ):
        scam_cat = "Digital Arrest / Authority Impersonation Scam"
        scam_conf = "HIGH"
        scam_desc = "The caller claims official authority or threatens legal arrest/penalties to coerce compliance or financial transfers."
    elif "BANK_FRAUD_UNAUTHORIZED" in categories_found:
        scam_cat = "Banking & Account KYC Fraud"
        scam_conf = "HIGH" if word_count >= 4 else "MEDIUM"
        scam_desc = "The caller fabricates account suspension or unauthorized transaction claims to extract credentials or funds."
    elif "FINANCIAL_REQUEST" in categories_found and ("URGENCY_PRESSURE" in categories_found or "AUTHORITY_IMPERSONATION" in categories_found or "SECRECY_COERCION" in categories_found):
        scam_cat = "Financial Transfer & Payment Scam"
        scam_conf = "HIGH"
        scam_desc = "High-pressure demands for urgent wire or money transfers detected under deceptive pretexts."
    elif "TECH_SUPPORT_SCAM" in categories_found:
        scam_cat = "Tech Support & Remote Access Scam"
        scam_conf = "HIGH"
        scam_desc = "The caller claims computer infection or urges installation of remote desktop management software (AnyDesk, TeamViewer)."
    elif "INVESTMENT_JOB_SCAM" in categories_found:
        scam_cat = "Investment & Advance Fee Scam"
        scam_conf = "HIGH"
        scam_desc = "The caller offers unrealistic investment returns or part-time task compensation requiring upfront deposits."
    elif "SIM_TELECOM_SCAM" in categories_found:
        scam_cat = "SIM & Telecom Deactivation Scam"
        scam_conf = "HIGH"
        scam_desc = "The caller threatens immediate phone line deactivation to harvest identity credentials."
    elif is_synthetic:
        scam_cat = "Synthetic / Cloned Voice Interaction"
        scam_conf = auth_conf
        scam_desc = "Acoustic vocoder analysis detected generative AI voice synthesis / cloned speech artifacts."
    elif not has_transcript:
        scam_cat = "Conversation Analysis Not Available"
        scam_conf = "UNCERTAIN"
        scam_desc = "Voice audio was analyzed acoustically, but spoken conversation content could not be transcribed."
    elif word_count < 4:
        scam_cat = "Listening for speech..."
        scam_conf = "LOW"
        scam_desc = "Awaiting sufficient conversational speech for threat analysis."
    elif len(detected_scam_indicators) == 0:
        scam_cat = "Routine / Normal Call"
        scam_conf = "HIGH" if word_count > 10 else "MEDIUM"
        scam_desc = "No high-confidence telecommunication scam, extortion, or synthetic voice indicators were detected."
    else:
        scam_cat = "Suspicious Call Pattern"
        scam_conf = "MEDIUM"
        scam_desc = "Linguistic and conversational patterns exhibit suspicious pressure or anomalies."

    # =========================================================================
    # STEP 4: OVERALL RISK SCORE & ESCALATION FLOORS
    # =========================================================================
    # Compute baseline conversational + contextual risk
    has_otp = "CREDENTIAL_OTP" in categories_found
    has_arrest = "DIGITAL_ARREST_LEGAL_THREAT" in categories_found
    has_finance = "FINANCIAL_REQUEST" in categories_found
    has_urgency = "URGENCY_PRESSURE" in categories_found
    has_secrecy = "SECRECY_COERCION" in categories_found
    severities = {ind.severity for ind in detected_scam_indicators}

    base_score = 0
    if has_otp:
        base_score = max(base_score, 85 if (has_finance or has_urgency) else 80)
    if has_arrest and (has_finance or has_urgency or has_secrecy):
        base_score = max(base_score, 90)
    if "CRITICAL" in severities:
        base_score = max(base_score, 80)
    elif "HIGH" in severities:
        base_score = max(base_score, 65)
    elif "MEDIUM" in severities:
        base_score = max(base_score, 40)
    elif context_risk:
        base_score = max(base_score, round(context_risk * 60))

    # SYNTHETIC VOICE ESCALATION FLOORS (AS MANDATED BY CENTRAL ARCHITECTURE):
    # Rule 8: If syntheticProbability >= 95 -> overallRisk = "CRITICAL RISK", threatScore >= 85
    # Rule 7: If syntheticProbability >= 85 -> overallRisk = "HIGH RISK", threatScore >= 70
    # Rule 6: If syntheticProbability >= 70 -> minimum "MEDIUM RISK", threatScore >= 50
    if synth_p >= 0.95 and is_synthetic:
        threat_score = max(base_score, 88)
        overall_risk = "CRITICAL RISK"
    elif synth_p >= 0.85 and is_synthetic:
        threat_score = max(base_score, 75)
        overall_risk = "HIGH RISK"
    elif synth_p >= 0.70 and is_synthetic:
        threat_score = max(base_score, 55)
        overall_risk = "MEDIUM RISK" if base_score < 70 else ("HIGH RISK" if base_score < 85 else "CRITICAL RISK")
    elif not is_synthetic:
        threat_score = base_score
        if threat_score >= 80:
            overall_risk = "CRITICAL RISK"
        elif threat_score >= 60:
            overall_risk = "HIGH RISK"
        elif threat_score >= 35:
            overall_risk = "MEDIUM RISK"
        else:
            overall_risk = "LOW RISK"
    else:
        threat_score = max(base_score, round(synth_p * 60))
        overall_risk = "MEDIUM RISK" if threat_score >= 40 else "LOW RISK"

    if not has_transcript and not is_chunk:
        risk_level = "PARTIAL_ANALYSIS"
    else:
        risk_level = overall_risk.replace(" RISK", "")

    # =========================================================================
    # STEP 5: RECOMMENDED ACTION & ANALYSIS REASONING
    # =========================================================================
    if is_synthetic:
        if len(detected_scam_indicators) > 0:
            recommended_action = (
                f"CRITICAL ACTION: AI-generated / cloned synthetic voice ({round(synth_p * 100)}% synthetic confidence) "
                f"detected alongside active scam indicators ({scam_cat}). Immediately disconnect and block this number. "
                "Do NOT transfer funds or provide sensitive banking credentials."
            )
            analysis_reasoning = (
                f"Forensic acoustic analysis detected high-confidence synthetic vocoder cloning artifacts ({round(synth_p * 100)}%). "
                f"Spoken conversation analysis detected {len(detected_scam_indicators)} fraudulent intent indicators."
            )
        else:
            recommended_action = (
                f"WARNING: AI-generated / cloned synthetic voice detected ({round(synth_p * 100)}% synthetic confidence). "
                "Verify caller identity through a secondary, trusted channel before sharing confidential personal or financial details."
            )
            analysis_reasoning = (
                f"Forensic acoustic analysis detected high-confidence synthetic vocoder cloning artifacts ({round(synth_p * 100)}%). "
                "No explicit fraud keywords were identified in the conversation transcript."
            )
    elif len(detected_scam_indicators) > 0:
        recommended_action = (
            f"CAUTION: Conversational threat indicators detected ({scam_cat}). "
            "Never share one-time passwords (OTP), PINs, or transfer money based on unsolicited telephone requests."
        )
        analysis_reasoning = f"Linguistic analysis detected {len(detected_scam_indicators)} telecommunication fraud threat indicators."
    else:
        recommended_action = "Routine call: No high-confidence telecommunication fraud or synthetic voice artifacts detected."
        analysis_reasoning = "Acoustic characteristics match natural biological human voice, and conversational intent matches normal dialogue."

    # =========================================================================
    # STEP 6: VALIDATION LAYER (SELF-CONSISTENCY GUARANTEE)
    # =========================================================================
    # Rule 10: IF scamCategory contains "Synthetic" OR voiceAuthenticity indicates AI/Synthetic:
    #   humanProbability cannot be greater than syntheticProbability
    #   voiceAuthenticity cannot be "Likely Human"
    #   overallRisk cannot be "LOW RISK"
    if "Synthetic" in scam_cat or is_synthetic or "Synthetic" in voice_auth_label:
        if human_prob > synth_p:
            logger.error("[VALIDATION CORRECTION] Inconsistency: human_prob > synth_p during synthetic classification. Normalizing.")
            human_prob, synth_p = synth_p, human_prob
        if voice_auth_label == "Likely Human":
            logger.error("[VALIDATION CORRECTION] Inconsistency: voice_auth_label was 'Likely Human' for synthetic voice. Normalizing to 'Likely Synthetic / AI Generated'.")
            voice_auth_label = "Likely Synthetic / AI Generated"
            is_synthetic = True
        if overall_risk == "LOW RISK":
            logger.error("[VALIDATION CORRECTION] Inconsistency: overall_risk was 'LOW RISK' for synthetic voice. Escalating to 'MEDIUM RISK'.")
            overall_risk = "MEDIUM RISK"
            threat_score = max(threat_score, 50)
        if "Synthetic / Cloned Voice Artifact" not in detected_threat_labels:
            detected_threat_labels.insert(0, "Synthetic / Cloned Voice Artifact")

    # Rule 9 / Anti-Contradiction: If voiceAuthenticity is "Likely Human", scamCategory CANNOT be "Synthetic / Cloned Voice Interaction"
    if voice_auth_label == "Likely Human":
        if scam_cat == "Synthetic / Cloned Voice Interaction":
            logger.error("[VALIDATION CORRECTION] Inconsistency: scam_cat was 'Synthetic / Cloned Voice Interaction' for human voice. Correcting to 'Routine / Normal Call'.")
            scam_cat = "Routine / Normal Call"
        detected_threat_labels = [lbl for lbl in detected_threat_labels if "Synthetic" not in lbl]

    # Assemble Structured Schemas
    voice_authenticity_detail = VoiceAuthenticityDetail(
        label=voice_auth_label,
        synthetic_probability=round(synth_p, 3),
        human_probability=round(human_prob, 3),
        confidence=auth_conf,
        model_name=df_result.model_name,
        analysis_status=auth_status,
        reasons=df_result.reasons,
    )

    synthetic_voice_evidence = SyntheticVoiceEvidence(
        detected=is_synthetic,
        confidence=auth_conf,
        synthetic_probability=round(synth_p, 3),
        evidence_summary=(
            f"Forensic acoustic classifier detected synthetic generation signatures ({round(synth_p * 100)}% probability)."
            if is_synthetic
            else "Acoustic characteristics match biological human vocal tract production."
        ),
    )

    unified_decision = UnifiedDecisionPayload(
        transcript=transcript,
        voiceAuthenticity=voice_auth_label,
        syntheticProbability=round(synth_p, 3),
        humanProbability=round(human_prob, 3),
        scamCategory=scam_cat,
        scamConfidence=scam_conf,
        threatScore=threat_score,
        overallRisk=overall_risk,
        detectedThreatIndicators=detected_threat_labels,
        recommendedAction=recommended_action,
        analysisReasoning=analysis_reasoning,
    )

    logger.info(
        f"[CENTRAL DECISION] Voice: {voice_auth_label} (Synth: {synth_p*100:.1f}%, Real: {human_prob*100:.1f}%) | "
        f"Category: {scam_cat} ({scam_conf}) | ThreatScore: {threat_score} | OverallRisk: {overall_risk}"
    )

    return {
        "voice_auth_label": voice_auth_label,
        "is_synthetic": is_synthetic,
        "synthetic_probability": round(synth_p, 3),
        "human_probability": round(human_prob, 3),
        "scam_category": scam_cat,
        "scam_confidence": scam_conf,
        "scam_description": scam_desc,
        "threat_score": threat_score,
        "risk_level": risk_level,
        "overall_risk": overall_risk,
        "recommended_action": recommended_action,
        "analysis_reasoning": analysis_reasoning,
        "indicators": indicators,
        "detected_threats": detected_threat_labels,
        "voice_authenticity_detail": voice_authenticity_detail,
        "synthetic_voice_evidence": synthetic_voice_evidence,
        "unified_decision": unified_decision,
    }
