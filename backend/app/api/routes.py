import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect

from app.api.websocket_manager import manager
from app.core.config import get_settings
from app.db import store
from app.models.schemas import (
    AnalysisHistoryResponse,
    AnalysisResponse,
    ContextRequest,
    ContextRiskResponse,
    HealthResponse,
    RiskWeights,
    ScamPredictionRequest,
    ScamPredictionResponse,
    SttResponse,
)
from app.services.analysis import analyze_audio_file
from app.services.audio.chunk_processor import live_stream_aggregator
from app.services.audio.preprocessing import load_audio
from app.services.detection.scam_classifier import predict_scam_text
from app.services.reporting import build_markdown_report
from app.services.risk.scoring import calculate_risk_detailed
from app.services.speaker.verification import extract_speaker_embedding, verify_speaker_identity
from app.services.stt.social_engineering import analyze_context_detailed
from app.services.stt.transcriber import transcribe_audio

router = APIRouter()



@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()

    deepfake_model_id = settings.deepfake_model_id
    if deepfake_model_id:
        BLOCKED_IDS = {
            "facebook/wav2vec2-base", "facebook/wav2vec2-large",
            "microsoft/wavlm-base", "microsoft/wavlm-large",
            "microsoft/wavlm-base-plus", "facebook/hubert-base-ls960",
        }
        if deepfake_model_id in BLOCKED_IDS or "wavlm-base-plus-sv" in deepfake_model_id:
            deepfake_model_status = "model_failed"
            active_model = "VoiceShield-Acoustic-v2 (CPU Native Heuristic Fallback)"
        else:
            deepfake_model_status = "pretrained_configured"
            active_model = deepfake_model_id
    else:
        deepfake_model_status = "heuristic_fallback_active"
        active_model = "VoiceShield-Acoustic-v2"

    return HealthResponse(
        status="healthy",
        service="voiceshield-ai-defense",
        phase="Phase-2-Defense-Hardened",
        model_name=active_model,
        deepfake_model_status=deepfake_model_status,
        speaker_model_status="handcrafted_baseline",
        device="cpu",
    )


@router.get("/risk/weights", response_model=RiskWeights)
def risk_weights() -> RiskWeights:
    settings = get_settings()
    return RiskWeights(
        deepfake=settings.deepfake_weight,
        prosody=settings.prosody_weight,
        speaker=settings.speaker_weight,
        context=settings.context_weight,
    )


@router.post("/scam/classify", response_model=ScamPredictionResponse)
@router.post("/predict/scam", response_model=ScamPredictionResponse)
def classify_scam_transcript(request: ScamPredictionRequest) -> ScamPredictionResponse:
    text = request.transcript or request.text or ""
    res = predict_scam_text(text)
    return ScamPredictionResponse(
        classification=res["classification"],
        confidence=res["confidence"],
        scam_probability=res["scam_probability"],
        risk_score=res["risk_score"],
        word_count=res["word_count"],
        model_status=res["model_status"],
        model_name="VoiceShield-NLP-Scam-Classifier-v1",
    )


@router.post("/context/analyze", response_model=ContextRiskResponse)
def analyze_transcript_context(request: ContextRequest) -> ContextRiskResponse:
    res = analyze_context_detailed(request.transcript)
    score, level, rec, breakdown = calculate_risk_detailed(
        deepfake_probability=0.0,
        prosody_score=0.0,
        speaker_mismatch=0.0,
        context_risk=res["context_risk"],
        detected_indicators=res["detected_indicators"],
        has_transcript=True,
    )
    if res.get("risk_level") == "Evaluating" and not res.get("detected_indicators"):
        level = "Evaluating"
        score = 0
        rec = "Listening for speech... Threat assessment will update in real time."

    evidence_list = breakdown.get("evidence_list", [])
    pts = breakdown.get("points_breakdown", {})

    return ContextRiskResponse(
        context_risk=res["context_risk"],
        context_risk_score=score,
        risk_level=level,
        classification=res.get("classification", "GENUINE"),
        confidence=res.get("confidence", 0.5),
        scam_probability=res.get("scam_probability", 0.0),
        nlp_model_status=res.get("nlp_model_status", "trained_nlp_pipeline"),
        possible_scam_category=res.get("possible_scam_category"),
        scam_category_confidence=res.get("scam_category_confidence"),
        scam_category_description=res.get("scam_category_description"),
        indicators=res["indicators"],
        detected_indicators=res["detected_indicators"],
        language=res["language"],
        evidence=evidence_list,
        final_risk_score=score,
        final_threat_level=level,
        final_scam_category=res.get("possible_scam_category"),
        recommendation=rec,
        conversation_risk_points=pts.get("conversation_threat_points", 0.0),
        voice_authenticity_points=pts.get("voice_authenticity_points", 0.0),
        behavioral_context_points=pts.get("behavioral_context_points", 0.0),
    )



@router.post("/audio/upload", response_model=AnalysisResponse)
async def upload_audio(
    file: UploadFile = File(...),
    transcript: str | None = Form(default=None),
    speaker_id: str | None = Form(default=None),
) -> AnalysisResponse:
    return await _analyze_upload(file, transcript, speaker_id)


@router.post("/audio/analyze", response_model=AnalysisResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    transcript: str | None = Form(default=None),
    speaker_id: str | None = Form(default=None),
) -> AnalysisResponse:
    return await _analyze_upload(file, transcript, speaker_id)


@router.post("/audio/chunk", response_model=AnalysisResponse)
async def analyze_audio_chunk(
    file: UploadFile = File(...),
    transcript: str | None = Form(default=None),
    speaker_id: str | None = Form(default=None),
) -> AnalysisResponse:
    response = await _analyze_upload(file, transcript, speaker_id, is_chunk=True)
    rolling_stats = live_stream_aggregator.update(
        current_risk_score=response.final_risk_score,
        latency_ms=response.inference_time_ms,
    )
    response.rolling_stats = rolling_stats
    await manager.broadcast({"type": "chunk", "payload": response.model_dump()})
    return response


@router.post("/stt/transcribe", response_model=SttResponse)
async def transcribe(file: UploadFile = File(...)) -> SttResponse:
    settings = get_settings()
    path = settings.temp_audio_dir / f"stt_{uuid4().hex}_{_clean_filename(file.filename)}"
    await _save_upload(file, path)
    response = transcribe_audio(path)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return response


@router.post("/speaker/register")
async def register_speaker(speaker_id: str = Form(...), file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    path = settings.reference_voice_dir / f"{speaker_id}_{uuid4().hex}_{_clean_filename(file.filename)}"
    await _save_upload(file, path)
    embedding = extract_speaker_embedding(path)
    created_at = datetime.now(UTC).isoformat()
    store.save_speaker(speaker_id, created_at, path, embedding)
    return {
        "speaker_id": speaker_id,
        "created_at": created_at,
        "status": "registered",
        "embedding_dimensions": len(embedding),
    }


@router.post("/speaker/verify")
async def verify_speaker(speaker_id: str = Form(...), file: UploadFile = File(...)) -> dict:
    speaker = store.get_speaker(speaker_id)
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker reference not found")
    settings = get_settings()
    path = settings.temp_audio_dir / f"verify_{uuid4().hex}_{_clean_filename(file.filename)}"
    await _save_upload(file, path)
    current_embedding = extract_speaker_embedding(path)
    result = verify_speaker_identity(current_embedding, speaker["embedding"])
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return {
        "speaker_id": speaker_id,
        "speaker_match_similarity": round(result.similarity, 3),
        "speaker_mismatch": round(result.speaker_mismatch, 3),
        "speaker_match_score": result.speaker_match_score,
        "speaker_match": result.speaker_match,
        "confidence": result.confidence,
    }


@router.post("/analysis/save")
@router.post("/analyses/save")
def save_custom_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    analysis_id = payload.get("analysis_id") or payload.get("id") or f"analysis_{uuid4().hex[:12]}"
    payload["analysis_id"] = analysis_id
    if "created_at" not in payload:
        payload["created_at"] = datetime.now(UTC).isoformat()
    store.save_analysis(payload)
    return {"status": "saved", "analysis_id": analysis_id}


@router.get("/analysis/{analysis_id}")
def get_analysis(analysis_id: str) -> dict[str, Any]:
    payload = store.get_analysis(analysis_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return payload


@router.get("/analyses", response_model=AnalysisHistoryResponse)
def list_recent_analyses(limit: int = 50) -> AnalysisHistoryResponse:
    return AnalysisHistoryResponse(analyses=store.list_analyses(max(1, min(limit, 100))))


@router.get("/analysis/{analysis_id}/report")
def get_analysis_report(analysis_id: str) -> Response:
    payload = store.get_analysis(analysis_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Analysis not found")
    report = build_markdown_report(AnalysisResponse(**payload))
    return Response(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="voice-shield-{analysis_id}.md"'},
    )


@router.websocket("/ws/live")
async def live_updates(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def _analyze_upload(
    file: UploadFile,
    transcript: str | None,
    speaker_id: str | None,
    is_chunk: bool = False,
) -> AnalysisResponse:
    settings = get_settings()
    prefix = "chunk_" if is_chunk else "audio_"
    clean_name = _clean_filename(file.filename)
    path = settings.temp_audio_dir / f"{prefix}{uuid4().hex}_{clean_name}"
    await _save_upload(file, path)

    reference_embedding = None
    if speaker_id:
        speaker = store.get_speaker(speaker_id)
        if speaker:
            reference_embedding = speaker["embedding"]

    try:
        response = analyze_audio_file(
            path=path,
            transcript=transcript,
            reference_embedding=reference_embedding,
            is_chunk=is_chunk,
        )
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    if not is_chunk:
        store.save_analysis(response.model_dump())
    return response


async def _save_upload(file: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)
    await file.seek(0)


def _clean_filename(filename: str | None) -> str:
    if not filename:
        return "input.wav"
    return Path(filename).name.replace(" ", "_")
