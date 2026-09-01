import concurrent.futures
import logging
import time
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

logger = logging.getLogger(__name__)


def analyze_audio_file(
    path: Path,
    transcript: str | None = None,
    reference_embedding: list[float] | None = None,
    is_chunk: bool = False,
) -> AnalysisResponse:
    t_start = time.perf_counter()

    # 1. Acoustic Loading & Audio Preparation (Single in-memory pass)
    t0_audio = time.perf_counter()
    audio = load_audio(path)
    features = extract_features(audio)
    samples, sr = load_audio_resampled(path, target_sr=16000)
    audio_prep_ms = (time.perf_counter() - t0_audio) * 1000

    # 2. AUDIO VALIDATION / SPEECH ACTIVITY GATE (VAD)
    t0_vad = time.perf_counter()
    min_dur = 0.25 if is_chunk else 0.35
    min_voiced = 0.12 if is_chunk else 0.18
    is_speech, reason, _ = validate_speech_activity(
        samples, sr, min_duration_sec=min_dur, min_voiced_duration_sec=min_voiced
    )
    vad_ms = (time.perf_counter() - t0_vad) * 1000

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

    # 3 & 4. Run Independent Acoustic/Deepfake & STT Transcription Concurrently
    def _run_acoustic_branch():
        t0 = time.perf_counter()
        df_res = detect_synthetic_voice_detailed(features, path)
        prosody_sc, prosody_rs = prosody_anomaly_score(features)
        ms = (time.perf_counter() - t0) * 1000
        return df_res, prosody_sc, prosody_rs, ms

    def _run_stt_branch():
        t0 = time.perf_counter()
        eff_tx = transcript
        if (not eff_tx or not eff_tx.strip()) and not is_chunk:
            stt_res = transcribe_audio(path=path, samples=samples)
            if stt_res.transcript and stt_res.transcript.strip():
                eff_tx = stt_res.transcript.strip()
        ms = (time.perf_counter() - t0) * 1000
        return eff_tx, ms

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_acoustic = executor.submit(_run_acoustic_branch)
        future_stt = executor.submit(_run_stt_branch)

        df_result, prosody_score, prosody_reasons, acoustic_ms = future_acoustic.result()
        effective_transcript, stt_ms = future_stt.result()

    deepfake_probability = df_result.synthetic_probability
    duration = features.duration_seconds or 0.0

    # 3-State Voice Authenticity Resolution
    if is_chunk or duration < 1.5:
        voice_authenticity = "INCONCLUSIVE"
        is_synthetic = False
    elif df_result.prediction == "SYNTHETIC" or deepfake_probability >= 0.70:
        voice_authenticity = "HIGH_CONFIDENCE_SYNTHETIC"
        is_synthetic = True
    elif deepfake_probability >= 0.50:
        voice_authenticity = "POSSIBLE_SYNTHETIC"
        is_synthetic = False
    elif deepfake_probability >= 0.30 or df_result.prediction == "INCONCLUSIVE":
        voice_authenticity = "INCONCLUSIVE"
        is_synthetic = False
    else:
        voice_authenticity = "LIKELY_HUMAN"
        is_synthetic = False

    # 5. NLP Scam Intent Analysis on Generated/Provided Transcript
    t0_nlp = time.perf_counter()
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
    nlp_ms = (time.perf_counter() - t0_nlp) * 1000

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
    t0_risk = time.perf_counter()
    final_score, risk_level, recommendation, breakdown = calculate_risk_detailed(
        deepfake_probability=deepfake_probability,
        prosody_score=prosody_score,
        speaker_mismatch=speaker_mismatch,
        context_risk=context_risk,
        has_speaker_reference=(reference_embedding is not None),
        detected_indicators=detected_scam_indicators,
        has_transcript=has_transcript,
    )
    risk_ms = (time.perf_counter() - t0_risk) * 1000

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

    total_ms = (time.perf_counter() - t_start) * 1000
    logger.info(
        f"[PERF] Pipeline Completed in {total_ms:.1f}ms "
        f"(AudioPrep={audio_prep_ms:.1f}ms, VAD={vad_ms:.1f}ms, STT={stt_ms:.1f}ms, "
        f"Acoustics={acoustic_ms:.1f}ms, NLP={nlp_ms:.1f}ms, RiskFusion={risk_ms:.1f}ms)"
    )

    detected_threats = [
        indicator.label for indicator in indicators if indicator.severity in {"MEDIUM", "HIGH", "CRITICAL"}
    ]

    if voice_authenticity == "HIGH_CONFIDENCE_SYNTHETIC":
        prediction_label = "SYNTHETIC"
    elif voice_authenticity == "POSSIBLE_SYNTHETIC":
        prediction_label = "POSSIBLE_SYNTHETIC"
    elif voice_authenticity == "INCONCLUSIVE":
        prediction_label = "INCONCLUSIVE"
    else:
        prediction_label = "REAL"

    response = AnalysisResponse(
        analysis_id=str(uuid4()),
        analysis_status=analysis_status,
        speech_detected=True,
        model_inference_skipped=False,
        prediction=prediction_label,
        voice_authenticity=voice_authenticity,
        confidence=round(max(deepfake_probability, 1.0 - deepfake_probability), 3),
        deepfake_probability=round(deepfake_probability, 3),
        speaker_match=round(1.0 - speaker_mismatch, 3) if reference_embedding is not None else None,
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
        inference_time_ms=round(total_ms, 2),
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

    # High-confidence synthetic voice detection on sustained speech
    if deepfake_probability >= 0.70 and duration >= 2.0 and not is_chunk:
        indicators.append(
            ThreatIndicator(
                label="Synthetic / Cloned Voice Artifact",
                severity="CRITICAL" if deepfake_probability >= 0.85 else "HIGH",
                detail=f"Acoustic forensic engine detected high-confidence synthetic cloning signatures ({round(deepfake_probability * 100)}%).",
                explanation="Acoustic analysis detected unnatural pitch step quantization, flattened dynamic envelope, or vocoder carrier artifacts.",
                why_it_matters="Synthetic speech signals generative AI voice cloning commonly used in impersonation scams.",
            )
        )
    elif deepfake_probability >= 0.50 and duration >= 2.0 and not is_chunk:
        indicators.append(
            ThreatIndicator(
                label="Suspicious Voice Modulation",
                severity="MEDIUM",
                detail=f"Acoustic characteristics exhibit elevated synthetic/vocoder traits ({round(deepfake_probability * 100)}%).",
                explanation="Constrained pitch dynamics or unnatural spectral flatness observed in voice phonation.",
                why_it_matters="Potential use of voice conversion software or low-bitrate generative speech synthesis.",
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


