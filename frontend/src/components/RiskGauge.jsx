import React from "react";

export function RiskGauge({ score = 0, level = "LOW" }) {
  const clamped = Math.max(0, Math.min(100, score));

  const getStatusMeta = () => {
    if (clamped < 25) {
      return {
        themeClass: "risk-theme-low",
        badgeText: "NO THREAT",
        verdict: "Voice interaction appears authentic with no significant fraud indicators.",
        action: "Normal interaction may proceed.",
      };
    }
    if (clamped < 50) {
      return {
        themeClass: "risk-theme-medium",
        badgeText: "LOW RISK",
        verdict: "Moderate acoustic anomalies or conversational sensitivity detected.",
        action: "Verify caller identity through an out-of-band channel before proceeding.",
      };
    }
    if (clamped < 75) {
      return {
        themeClass: "risk-theme-high",
        badgeText: "HIGH RISK",
        verdict: "Synthetic voice characteristics or explicit financial coercion detected.",
        action: "Do not execute requested transactions or disclose credentials.",
      };
    }
    return {
      themeClass: "risk-theme-critical",
      badgeText: "CRITICAL RISK",
      verdict: "High-confidence synthetic voice generation or active social engineering.",
      action: "Terminate call immediately and report potential fraud attempt.",
    };
  };

  const meta = getStatusMeta();

  return (
    <div className={`assessment-card ${meta.themeClass}`}>
      <div className="assessment-header">
        <span className="assessment-label">OVERALL THREAT ASSESSMENT</span>
        <span className="assessment-badge">{meta.badgeText}</span>
      </div>

      <div className="assessment-content">
        <div className="score-block">
          <div className="score-number">{clamped}</div>
          <div className="score-denom">/ 100</div>
          <div className="score-level">{level} RISK</div>
        </div>

        <div className="assessment-details">
          <p className="assessment-verdict">{meta.verdict}</p>
          <div className="assessment-action-row">
            <span className="action-tag">Recommended Action:</span>
            <span className="action-text">{meta.action}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
