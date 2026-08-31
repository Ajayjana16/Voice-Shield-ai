from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.db import store
from app.models.schemas import AnalysisResponse, ThreatIndicator
from app.services.audio.preprocessing import (
    extract_features,
    load_audio,
    load_audio_resampled,
    validate_speech_activity,
)
from app.services.detection.deepfake import detect_synthetic_voice_detailed
from app.services.prosody.analyzer import prosody_anomaly_score
from app.services.risk.scoring import calculate_risk_detailed
from app.services.speaker.verification import extract_speaker_embedding, verify_speaker_identity
from app.services.stt.social_engineering import analyze_context_detailed, infer_scam_category
from app.services.stt.transcriber import transcribe_audio


def analyze_audio_file(
    path: Path,
    transcript: str | None = None,
    reference_embedding: list[float] | None = None,
    is_chunk: bool = False,
) -> AnalysisResponse:
    # 1. Acoustic Loading & Feature Extraction
    audio = load_audio(path)
    features = extract_features(audio)

    # 2. AUDIO VALIDATION / SPEECH ACTIVITY GATE (VAD)
    samples, sr = load_audio_resampled(path, target_sr=16000)
    min_dur = 0.25 if is_chunk else 0.35
    min_voiced = 0.12 if is_chunk else 0.18
    is_speech, reason, _ = validate_speech_activity(
        samples, sr, min_duration_sec=min_dur, min_voiced_duration_sec=min_voiced
    )

    if not is_speech:
        # DO NOT run the threat scoring pipeline on silent or near-silent audio.
        response = AnalysisResponse(
            analysis_id=str(uuid4()),
            analysis_status="insufficient_audio",
            speech_detected=False,
            model_inference_skipped=True,
            skip_reason="insufficient_speech_audio",
            reason="No sufficient speech or meaningful audio was detected for reliable analysis.",
            prediction="NOT_ANALYZED",
            voice_authenticity="NOT_ANALYZED",
            confidence=None,
            deepfake_probability=None,
            speaker_match=None,
            speaker_mismatch=None,
            speaker_match_score=None,
            speaker_match_confidence=None,
            prosody_score=None,
            context_risk=None,
            final_risk_score=None,
            risk_level="NOT_ANALYZED",
            risk_reasoning="Threat scoring skipped due to absence of detectable voiced speech.",
            possible_scam_category=None,
            scam_category_confidence=None,
            scam_category_description=None,
            recommendation="No speech detected. Please speak clearly for at least 2-3 seconds and try again.",
            detected_threats=[],
            scam_indicators=[],
            indicators=[],
            features=features,
            transcript=transcript,
            created_at=datetime.now(UTC).isoformat(),
            model_name=get_settings().deepfake_model_id or "VoiceShield-Acoustic-v2",
            inference_time_ms=0.0,
            fallback_used=False,
            rolling_stats=None,
            risk_breakdown=None,
        )
        if not is_chunk:
            store.save_analysis(response.model_dump())
        return response

    # 3. Deepfake / Synthetic Voice Detection (Independent Signal)
    df_result = detect_synthetic_voice_detailed(features, path)
    deepfake_probability = df_result.synthetic_probability
    duration = features.duration_seconds or 0.0

    # Minimum evidence gate: Short recordings (<3.5s) or streaming chunks cannot produce strong synthetic conclusions
    if is_chunk or duration < 3.5:
        voice_authenticity = "INCONCLUSIVE"
        is_synthetic = False
        deepfake_probability = min(deepfake_probability, 0.08)
    elif df_result.model_type == "pretrained_antispoofing" and not df_result.fallback_used:
        # Full pretrained neural model with sufficient duration
        if deepfake_probability >= 0.85:
            voice_authenticity = "HIGH_CONFIDENCE_SYNTHETIC"
            is_synthetic = True
        elif deepfake_probability >= 0.70:
            voice_authenticity = "POSSIBLE_SYNTHETIC"
            is_synthetic = False
        elif deepfake_probability >= 0.35:
            voice_authenticity = "INCONCLUSIVE"
            is_synthetic = False
        else:
            voice_authenticity = "LIKELY_HUMAN"
            is_synthetic = False
    else:
        # Acoustic baseline fallback (No confirmed neural deepfake model)
        # Normal microphone speech is biological human speech
        voice_authenticity = "LIKELY_HUMAN"
        is_synthetic = False
        deepfake_probability = min(deepfake_probability, 0.08)



    # 4. Prosody Anomaly Analysis (Independent Signal)
    prosody_score, prosody_reasons = prosody_anomaly_score(features)

    # 5. Speech-to-Text & Conversation Scam Intent Analysis
    effective_transcript = transcript
    if not effective_transcript or not effective_transcript.strip():
        # Attempt automatic server-side transcription
        stt_resp = transcribe_audio(path)
        if stt_resp.transcript and stt_resp.transcript.strip():
            effective_transcript = stt_resp.transcript.strip()

    has_transcript = bool(effective_transcript and effective_transcript.strip())
    
    if has_transcript:
        ctx_result = analyze_context_detailed(effective_transcript)
        context_risk = ctx_result["context_risk"]
        detected_scam_indicators = ctx_result["detected_indicators"]
        analysis_status = "completed"
        possible_category, category_confidence, category_desc = infer_scam_category(
            detected_indicators=detected_scam_indicators,
            is_synthetic=is_synthetic,
            deepfake_prob=deepfake_probability,
        )
    else:
        context_risk = None
        detected_scam_indicators = []
        analysis_status = "partial_analysis"
        possible_category = "Conversation Analysis Not Available"
        category_confidence = "UNCERTAIN"
        category_desc = "Voice audio was analyzed, but spoken conversation content could not be reliably transcribed. Scam detection based on call content was not completed."

    # 6. Speaker Biometric Verification (Optional / Enterprise)
    speaker_match_score = None
    speaker_match_bool = None
    speaker_match_conf = None
    speaker_similarity = None
    speaker_mismatch = 0.0

    if reference_embedding:
        current_embedding = extract_speaker_embedding(path, features)
        spk_result = verify_speaker_identity(current_embedding, reference_embedding)
        speaker_match_score = spk_result.speaker_match_score
        speaker_match_bool = spk_result.speaker_match
        speaker_match_conf = spk_result.confidence
        speaker_similarity = spk_result.similarity
        speaker_mismatch = spk_result.speaker_mismatch

    # 7. Security-Aware Risk Fusion Engine
    final_score, risk_level, recommendation, breakdown = calculate_risk_detailed(
        deepfake_probability=deepfake_probability,
        prosody_score=prosody_score,
        speaker_mismatch=speaker_mismatch,
        context_risk=context_risk,
        has_speaker_reference=(reference_embedding is not None),
        detected_indicators=detected_scam_indicators,
        has_transcript=has_transcript,
    )

    # 8. Threat Indicators & Evidence Assembly
    indicators = _build_indicators(
        deepfake_probability=deepfake_probability,
        context_indicators=detected_scam_indicators,
        speaker_mismatch=speaker_mismatch,
        has_speaker_ref=(reference_embedding is not None),
        is_neural_model=(df_result.model_type == "pretrained_antispoofing" and not df_result.fallback_used),
        duration=duration,
        is_chunk=is_chunk,
    )
    detected_threats = [
        indicator.label for indicator in indicators if indicator.severity in {"MEDIUM", "HIGH", "CRITICAL"}
    ]

    prediction_label = "SYNTHETIC" if (is_synthetic and deepfake_probability >= 0.50) else "REAL"

    response = AnalysisResponse(
        analysis_id=str(uuid4()),
        analysis_status=analysis_status,
        speech_detected=True,
        model_inference_skipped=False,
        prediction=prediction_label,
        voice_authenticity=voice_authenticity,
        confidence=round(max(deepfake_probability, 1.0 - deepfake_probability), 3),
        deepfake_probability=round(deepfake_probability, 3),
        speaker_match=speaker_similarity,
        speaker_mismatch=round(speaker_mismatch, 3) if reference_embedding else None,
        speaker_match_score=speaker_match_score,
        speaker_match_confidence=speaker_match_conf,
        prosody_score=round(prosody_score, 3),
        context_risk=round(context_risk, 3) if context_risk is not None else None,
        final_risk_score=final_score,
        risk_level=risk_level,
        risk_reasoning=breakdown.get("risk_reasoning"),
        possible_scam_category=possible_category,
        scam_category_confidence=category_confidence,
        scam_category_description=category_desc,
        recommendation=recommendation,
        detected_threats=detected_threats,
        scam_indicators=detected_scam_indicators,
        indicators=indicators,
        features=features,
        transcript=effective_transcript,
        created_at=datetime.now(UTC).isoformat(),
        model_name=df_result.model_name,
        inference_time_ms=df_result.inference_time_ms,
        fallback_used=df_result.fallback_used,
        risk_breakdown=breakdown,
    )

    if not is_chunk:
        store.save_analysis(response.model_dump())
    return response


def _build_indicators(
    deepfake_probability: float,
    context_indicators: list[Any],
    speaker_mismatch: float,
    has_speaker_ref: bool,
    is_neural_model: bool = False,
    duration: float = 0.0,
    is_chunk: bool = False,
) -> list[ThreatIndicator]:
    indicators: list[ThreatIndicator] = []

    # High-confidence neural anti-spoofing detection on sustained speech only
    if is_neural_model and deepfake_probability >= 0.85 and duration >= 3.5 and not is_chunk:
        indicators.append(
            ThreatIndicator(
                label="Synthetic Voice Artifact",
                severity="HIGH",
                detail=f"Pretrained anti-spoofing model detected high-confidence synthetic cloning ({round(deepfake_probability * 100)}%).",
                explanation="Neural anti-spoofing classifier detected vocoder artifacts or generative voice cloning.",
                why_it_matters="Synthetic speech signals generative voice cloning commonly used in impersonation scams.",
            )
        )

    for item in context_indicators:
        matched_str = f"Evidence: \"{item.matched_cue}\"" if item.matched_cue else ""
        indicators.append(
            ThreatIndicator(
                label=item.label,
                severity=item.severity,
                detail=matched_str or item.category,
                explanation=item.explanation or f"Detected language patterns matching {item.label}.",
                why_it_matters=item.why_it_matters or "This pattern is a frequent indicator of telecommunication fraud.",
            )
        )

    if has_speaker_ref and speaker_mismatch >= 0.35:
        match_pct = round((1.0 - speaker_mismatch) * 100)
        severity = "CRITICAL" if speaker_mismatch >= 0.55 else "HIGH"
        indicators.append(
            ThreatIndicator(
                label="Speaker Identity Mismatch",
                severity=severity,
                detail=f"Claimed reference voice biometric match is only {match_pct}%",
                explanation="Voice acoustics deviate significantly from the enrolled speaker baseline.",
                why_it_matters="Indicates a caller impersonating an authorized individual.",
            )
        )

    return indicators


