import React from "react";

export function getThreatExplanation(ind) {
  if (
    ind.explanation &&
    ind.explanation !== "Detected telecommunication deception cue." &&
    ind.explanation !== "Identified conversational deception indicator."
  ) {
    return ind.explanation;
  }
  if (
    ind.why_it_matters &&
    ind.why_it_matters !== "Detected telecommunication deception cue." &&
    ind.why_it_matters !== "Identified conversational deception indicator."
  ) {
    return ind.why_it_matters;
  }

  const name = (ind.label || ind.category || ind.title || "").toLowerCase();
  if (name.includes("otp") || name.includes("credential") || name.includes("pin") || name.includes("password") || name.includes("cvv")) {
    return "The caller requested a one-time password (OTP), PIN, or confidential account credentials.";
  }
  if (name.includes("digital arrest") || name.includes("police extortion") || name.includes("arrest warrant") || name.includes("arrest")) {
    return "The caller threatened immediate arrest, criminal prosecution, or detention to coerce compliance.";
  }
  if (name.includes("authority") || name.includes("police") || name.includes("cbi") || name.includes("government") || name.includes("customs")) {
    return "The caller claimed official authority from law enforcement or a regulatory agency.";
  }
  if (name.includes("transfer") || name.includes("payment") || name.includes("finance") || name.includes("fee") || name.includes("wire")) {
    return "The caller demanded an immediate financial transfer, security deposit, or fee payment.";
  }
  if (name.includes("urgency") || name.includes("pressure") || name.includes("time")) {
    return "The caller used urgency or pressure tactics to force immediate action.";
  }
  if (name.includes("bank") || name.includes("kyc") || name.includes("block") || name.includes("suspension") || name.includes("deactivation")) {
    return "The caller claimed a bank account or card will be suspended or blocked.";
  }
  if (name.includes("parcel") || name.includes("contraband") || name.includes("courier") || name.includes("package")) {
    return "The caller claimed an intercepted parcel contains illegal contraband or narcotics.";
  }
  if (name.includes("secrecy") || name.includes("isolation")) {
    return "The caller demanded strict secrecy to prevent independent verification with family or banks.";
  }
  if (name.includes("investment") || name.includes("job") || name.includes("lottery") || name.includes("grant") || name.includes("crypto")) {
    return "The caller promised high guaranteed returns, job commissions, or requested an upfront deposit.";
  }
  if (name.includes("blackmail") || name.includes("extortion")) {
    return "The caller threatened reputational damage, video release, or harm unless ransom is paid.";
  }
  if (name.includes("synthetic") || name.includes("voice") || name.includes("deepfake")) {
    return "Neural audio classifier identified synthetic vocoder artifacts in the voice stream.";
  }
  if (name.includes("ai scam") || name.includes("nlp")) {
    return "Trained NLP model detected high-confidence fraudulent intent in the spoken conversation.";
  }
  return "Detected telecommunication fraud pattern and social engineering tactics in the conversation.";
}

export default function ThreatSignalCard({ signal, index }) {
  if (!signal) return null;

  const title = signal.label || signal.category || signal.title || (typeof signal === "string" ? signal : "Detected Threat Signal");
  const rawSev = (signal.severity || "HIGH").toUpperCase();
  const severity = rawSev === "CRITICAL" ? "CRITICAL" : rawSev === "LOW" ? "LOW" : "HIGH";

  const dotClass = severity === "CRITICAL" ? "dot-critical" : severity === "LOW" ? "dot-low" : "dot-high";
  const badgeClass = severity === "CRITICAL" ? "badge-critical" : severity === "LOW" ? "badge-low" : "badge-high";

  const explanation = getThreatExplanation(signal);
  const matchedCue = signal.matched_cue || signal.evidence || signal.matched_phrase || null;

  return (
    <div className="threat-signal-card" key={index}>
      {/* Top Row: Severity Dot + Threat Name (Left) ... Severity Badge (Right) */}
      <div className="threat-signal-header">
        <div className="threat-signal-title-group">
          <span className={`threat-signal-dot ${dotClass}`} />
          <strong className="threat-signal-name">{title}</strong>
        </div>
        <span className={`threat-signal-badge ${badgeClass}`}>{severity}</span>
      </div>

      {/* Middle Row: Concise Explanation */}
      <p className="threat-signal-explanation">{explanation}</p>

      {/* Bottom Row: Matched Transcript Evidence */}
      {matchedCue && (
        <div className="threat-signal-evidence">
          <span className="threat-signal-evidence-label">Detected phrase:</span>
          <span className="threat-signal-evidence-text">&quot;{matchedCue}&quot;</span>
        </div>
      )}
    </div>
  );
}
