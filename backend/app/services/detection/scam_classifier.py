"""
Scam vs Non-Scam NLP Classification Model Service.
Loads the trained pipeline (TF-IDF + Soft Voting Ensemble: LogisticRegression, ComplementNB, Calibrated SGD)
and exposes clean prediction endpoints for Voice Shield.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

# Locate saved model
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "saved" / "scam_classifier" / "scam_classifier_pipeline.joblib"

_MODEL_BUNDLE: dict[str, Any] | None = None


def get_model_bundle() -> dict[str, Any] | None:
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None:
        if MODEL_PATH.exists():
            try:
                _MODEL_BUNDLE = joblib.load(str(MODEL_PATH))
                logger.info("Successfully loaded NLP Scam Classifier from %s", MODEL_PATH)
            except Exception as e:
                logger.error("Failed to load scam classifier model: %s", e)
                _MODEL_BUNDLE = None
        else:
            logger.warning("Scam classifier model file not found at %s", MODEL_PATH)
    return _MODEL_BUNDLE


def clean_text_for_inference(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r'^\d+[\.\)]\s*', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def predict_scam_text(transcript: str | None) -> dict[str, Any]:
    """
    Predict whether a transcript is SCAM or GENUINE using the trained NLP classifier.
    Returns:
      - classification: "SCAM" | "GENUINE"
      - confidence: float (0.0 to 1.0)
      - scam_probability: float (0.0 to 1.0)
      - risk_score: int (0 to 100)
      - word_count: int
      - model_status: str
    """
    if not transcript or not transcript.strip():
        return {
            "classification": "GENUINE",
            "confidence": 1.0,
            "scam_probability": 0.0,
            "risk_score": 0,
            "word_count": 0,
            "model_status": "empty_input",
        }

    cleaned = clean_text_for_inference(transcript)
    words = cleaned.split()
    word_count = len(words)

    # Context stability check: Avoid unstable predictions on 1-2 words unless high-risk keyword is present
    if word_count < 3:
        high_risk_trigger = bool(
            re.search(r'\b(otp|one[- ]time[- ]password|cvv|mpin|digital[- ]arrest|arrest[- ]warrant|police[- ]case|cbi|customs[- ]parcel|contraband)\b', cleaned, re.IGNORECASE)
        )
        if not high_risk_trigger:
            return {
                "classification": "GENUINE",
                "confidence": 0.5,
                "scam_probability": 0.05,
                "risk_score": 5,
                "word_count": word_count,
                "model_status": "insufficient_text_context",
            }

    bundle = get_model_bundle()
    if bundle is None or "pipeline" not in bundle:
        # Fallback to conservative evaluation if model is not loaded
        return {
            "classification": "GENUINE",
            "confidence": 0.5,
            "scam_probability": 0.1,
            "risk_score": 10,
            "word_count": word_count,
            "model_status": "fallback_no_model",
        }

    pipeline = bundle["pipeline"]
    try:
        proba = pipeline.predict_proba([cleaned])[0]
        # proba[0] = GENUINE, proba[1] = SCAM
        p_genuine = float(proba[0])
        p_scam = float(proba[1])

        if p_scam >= 0.50:
            classification = "SCAM"
            confidence = round(p_scam, 4)
            risk_score = min(100, max(50, round(p_scam * 100)))
        else:
            classification = "GENUINE"
            confidence = round(p_genuine, 4)
            # Low genuine risk score
            risk_score = max(0, min(24, round(p_scam * 100)))

        return {
            "classification": classification,
            "confidence": confidence,
            "scam_probability": round(p_scam, 4),
            "risk_score": risk_score,
            "word_count": word_count,
            "model_status": "trained_nlp_pipeline",
            "model_accuracy": bundle.get("accuracy", 0.9937),
            "model_f1": bundle.get("f1", 0.9937),
        }
    except Exception as err:
        logger.error("Scam classification error: %s", err)
        return {
            "classification": "GENUINE",
            "confidence": 0.5,
            "scam_probability": 0.0,
            "risk_score": 0,
            "word_count": word_count,
            "model_status": "inference_error",
        }
