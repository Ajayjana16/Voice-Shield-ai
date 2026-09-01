from typing import Any
from pydantic import BaseModel, Field


class AcousticFeatures(BaseModel):
    duration_seconds: float
    sample_rate: int | None
    rms_energy: float
    zero_crossing_rate: float
    spectral_centroid: float
    spectral_contrast: float
    pitch_hz: float
    pause_ratio: float
    dynamic_range: float
    byte_entropy: float


class ThreatIndicator(BaseModel):
    label: str
    severity: str
    detail: str
    explanation: str | None = None
    why_it_matters: str | None = None


class DeepfakeDetectionResult(BaseModel):
    prediction: str = "REAL"  # "REAL" or "SYNTHETIC" or "NOT_ANALYZED"
    synthetic_probability: float = Field(default=0.0, ge=0, le=1)
    real_probability: float = Field(default=1.0, ge=0, le=1)
    model_name: str = "VoiceShield-Acoustic-v2"
    model_type: str = "heuristic_fallback"  # "pretrained_antispoofing" | "heuristic_fallback" | "legacy_embedding"
    model_status: str = "loaded"  # "loaded" | "failed" | "unavailable" | "no_model_configured" | "skipped"
    model_inference_skipped: bool = False
    skip_reason: str | None = None
    inference_time_ms: float = 0.0
    fallback_used: bool = False
    reasons: list[str] = Field(default_factory=list)


class SpeakerVerificationResult(BaseModel):
    speaker_match_score: int = Field(default=0, ge=0, le=100)
    speaker_match: bool = False
    similarity: float = Field(default=0.0, ge=0, le=1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    speaker_mismatch: float = Field(default=1.0, ge=0, le=1)


class RollingAnalysisStats(BaseModel):
    latest_score: int | None = 0
    rolling_average: float = 0.0
    max_recent_risk: int = 0
    chunk_count: int = 0
    trend: str = "STABLE"  # "RISING", "FALLING", "STABLE", "WAITING_FOR_SPEECH"
    latency_ms: float = 0.0
    detected_indicators: list[str] = Field(default_factory=list)
    possible_scam_category: str | None = None


class DetectedContextIndicator(BaseModel):
    category: str
    label: str
    severity: str
    matched_cue: str | None = None
    weight: float = 0.0
    explanation: str | None = None
    why_it_matters: str | None = None


class VoiceAuthenticityDetail(BaseModel):
    label: str = "LIKELY_HUMAN"  # "LIKELY_HUMAN" | "LIKELY_SYNTHETIC" | "INCONCLUSIVE" | "ANALYSIS_FAILED" | "NOT_EVALUATED"
    synthetic_probability: float = 0.0  # 0.0 to 1.0
    human_probability: float = 1.0  # 0.0 to 1.0
    confidence: str = "HIGH"  # "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN" | "N/A"
    model_name: str = "VoiceShield-Forensic-Acoustic-v3"
    analysis_status: str = "completed"  # "completed" | "skipped" | "failed" | "not_evaluated"
    reasons: list[str] = Field(default_factory=list)


class SyntheticVoiceEvidence(BaseModel):
    detected: bool = False
    confidence: str = "LOW"  # "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN"
    synthetic_probability: float = 0.0
    evidence_summary: str | None = None


class UnifiedDecisionPayload(BaseModel):
    transcript: str | None = None
    voiceAuthenticity: str = "Likely Human"
    syntheticProbability: float = 0.0
    humanProbability: float = 1.0
    scamCategory: str = "Routine / Normal Call"
    scamConfidence: str = "HIGH"
    threatScore: int = 0
    overallRisk: str = "LOW RISK"
    detectedThreatIndicators: list[str] = Field(default_factory=list)
    recommendedAction: str = ""
    analysisReasoning: str = ""


class AnalysisResponse(BaseModel):
    analysis_id: str
    analysis_status: str = "completed"  # "completed" | "insufficient_audio" | "error"
    speech_detected: bool = True
    model_inference_skipped: bool = False
    skip_reason: str | None = None
    reason: str | None = None
    prediction: str = "REAL"  # "REAL" | "SYNTHETIC" | "FAKE" | "NOT_ANALYZED"
    voice_authenticity: str = "LIKELY_HUMAN"  # "Likely Synthetic / AI Generated" | "Likely Human" | "Uncertain" | "Voice authenticity analysis unavailable"
    voice_authenticity_detail: VoiceAuthenticityDetail | None = None
    synthetic_voice_evidence: SyntheticVoiceEvidence | None = None
    unified_decision: UnifiedDecisionPayload | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    deepfake_probability: float | None = Field(default=None, ge=0, le=1)
    real_probability: float | None = Field(default=None, ge=0, le=1)
    speaker_match: float | None = Field(default=None, ge=0, le=1)
    speaker_mismatch: float | None = Field(default=None, ge=0, le=1)
    speaker_match_score: int | None = Field(default=None, ge=0, le=100)
    speaker_match_confidence: float | None = Field(default=None, ge=0, le=1)
    prosody_score: float | None = Field(default=None, ge=0, le=1)
    context_risk: float | None = Field(default=None, ge=0, le=1)
    final_risk_score: int | None = Field(default=None, ge=0, le=100)
    risk_level: str = "NOT_ANALYZED"  # "NOT_ANALYZED" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    risk_reasoning: str | None = None
    possible_scam_category: str | None = None
    scam_category_confidence: str | None = None  # "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN"
    scam_category_description: str | None = None
    recommendation: str
    detected_threats: list[str] = Field(default_factory=list)
    scam_indicators: list[DetectedContextIndicator] = Field(default_factory=list)
    indicators: list[ThreatIndicator] = Field(default_factory=list)
    features: AcousticFeatures | None = None
    transcript: str | None = None
    created_at: str
    model_name: str = "VoiceShield-Acoustic-v2"
    inference_time_ms: float = 0.0
    fallback_used: bool = False
    rolling_stats: RollingAnalysisStats | None = None
    risk_breakdown: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    phase: str
    model_name: str = "VoiceShield-Acoustic-v2"
    deepfake_model_status: str = "heuristic_fallback_active"  # "pretrained_active" | "heuristic_fallback_active" | "model_failed" | "no_model_configured"
    speaker_model_status: str = "handcrafted_baseline"
    device: str = "cpu"
    features_supported: list[str] = Field(
        default_factory=lambda: [
            "deepfake_detection",
            "telecom_scam_detection",
            "social_engineering_analysis",
            "authority_impersonation_detection",
            "financial_fraud_detection",
            "multilingual_indian_languages",
            "live_chunk_streaming",
        ]
    )


class RiskWeights(BaseModel):
    deepfake: float = 0.45
    prosody: float = 0.15
    speaker: float = 0.20
    context: float = 0.20


class ContextRequest(BaseModel):
    transcript: str


class ContextRiskResponse(BaseModel):
    context_risk: float = Field(ge=0, le=1)
    context_risk_score: int = Field(default=0, ge=0, le=100)
    risk_level: str
    classification: str = "GENUINE"  # "SCAM" | "GENUINE"
    confidence: float | None = None
    scam_probability: float | None = None
    nlp_model_status: str | None = "trained_nlp_pipeline"
    possible_scam_category: str | None = None
    scam_category_confidence: str | None = None
    scam_category_description: str | None = None
    indicators: list[str]
    detected_indicators: list[DetectedContextIndicator] = Field(default_factory=list)
    language: str = "multilingual"
    evidence: list[str] = Field(default_factory=list)
    final_risk_score: int = Field(default=0, ge=0, le=100)
    final_threat_level: str = "LOW"
    final_scam_category: str | None = None
    recommendation: str | None = None
    conversation_risk_points: float = 0.0
    voice_authenticity_points: float = 0.0
    behavioral_context_points: float = 0.0


class ScamPredictionRequest(BaseModel):
    text: str | None = None
    transcript: str | None = None


class ScamPredictionResponse(BaseModel):
    classification: str  # "SCAM" | "GENUINE"
    confidence: float = Field(ge=0, le=1)
    scam_probability: float = Field(ge=0, le=1)
    risk_score: int = Field(ge=0, le=100)
    word_count: int = 0
    model_status: str = "trained_nlp_pipeline"
    model_name: str = "VoiceShield-NLP-Scam-Classifier-v1"



class AnalysisSummary(BaseModel):
    analysis_id: str
    created_at: str
    analysis_status: str = "completed"
    risk_level: str
    final_risk_score: int | None = Field(default=None, ge=0, le=100)
    prediction: str = "REAL"
    voice_authenticity: str | None = "LIKELY_HUMAN"
    possible_scam_category: str | None = None
    model_name: str = "VoiceShield-Acoustic-v2"


class AnalysisHistoryResponse(BaseModel):
    analyses: list[AnalysisSummary]


class SttResponse(BaseModel):
    transcript: str
    provider: str
    confidence: float = Field(ge=0, le=1)
    warning: str | None = None
