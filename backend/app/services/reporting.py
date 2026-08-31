from app.models.schemas import AnalysisResponse


def build_markdown_report(analysis: AnalysisResponse) -> str:
    is_insufficient = analysis.analysis_status == "insufficient_audio"

    if is_insufficient:
        return f"""# Voice Shield Security Evaluation Report

**Analysis ID**: `{analysis.analysis_id}`  
**Created**: `{analysis.created_at}`  
**Evaluation Status**: `NO SPEECH DETECTED (NOT ANALYZED)`

---

## Assessment Summary
- **Overall Threat Level**: `NOT ANALYZED`
- **Threat Score**: `-- / 100`
- **Voice Authenticity**: `NOT ANALYZED`
- **Possible Scam Category**: `None (No speech audio)`

## Advisory
{analysis.recommendation}
"""

    threats = "\n".join(f"- {threat}" for threat in analysis.detected_threats) or "- No high-severity threats detected"
    
    indicators_md = []
    for indicator in analysis.indicators:
        item = f"### {indicator.label} (`{indicator.severity}`)\n"
        if indicator.explanation:
            item += f"- **What was detected**: {indicator.explanation}\n"
        if indicator.why_it_matters:
            item += f"- **Why it matters**: {indicator.why_it_matters}\n"
        item += f"- **Diagnostic detail**: {indicator.detail}\n"
        indicators_md.append(item)
    
    indicators_section = "\n".join(indicators_md) if indicators_md else "- No supporting indicators"

    df_pct = f"{round(analysis.deepfake_probability * 100)}%" if analysis.deepfake_probability is not None else "--"
    ctx_pct = f"{round(analysis.context_risk * 100)}%" if analysis.context_risk is not None else "--"
    transcript = analysis.transcript or "No transcript provided"
    scam_category = analysis.possible_scam_category or "Suspicious Activity — Category Uncertain"
    scam_confidence = analysis.scam_category_confidence or "LOW"
    voice_auth = analysis.voice_authenticity.replace("_", " ").title() if analysis.voice_authenticity else "Likely Human"

    return f"""# Voice Shield Security Evaluation Report

**Analysis ID**: `{analysis.analysis_id}`  
**Created**: `{analysis.created_at}`  
**Engine**: `{analysis.model_name}` ({'Heuristic Fallback' if analysis.fallback_used else 'Pretrained Neural Model'})

---

## 1. Overall Threat Assessment
- **Threat Level**: **{analysis.risk_level} RISK**
- **Threat Score**: **{analysis.final_risk_score} / 100**
- **Possible Scam Category**: **{scam_category}** (Confidence: `{scam_confidence}`)
- **Voice Authenticity**: **{voice_auth}** (Synthetic Probability: `{df_pct}`)

> **Security Reasoning**: {analysis.risk_reasoning or 'Multi-signal evaluation completed.'}

---

## 2. Recommended Action
{analysis.recommendation}

---

## 3. Detected Threat & Scam Indicators
{indicators_section}

---

## 4. Signal Telemetry
- **Synthetic Voice Probability**: `{df_pct}`
- **Conversation & Scam Risk**: `{ctx_pct}`
- **Acoustic Prosody Score**: `{round((analysis.prosody_score or 0) * 100)}%`
- **Inference Latency**: `{analysis.inference_time_ms} ms`

---

## 5. Conversation Transcript Evaluated
```text
{transcript}
```

---
*Report generated securely by Voice Shield AI — Local ephemeral audio processing.*
"""
