/**
 * Lightweight contextual normalization layer for speech-to-text transcripts.
 * Corrects common speech recognition errors for fraud keywords (such as ATP -> OTP)
 * when paired with intent verbs, while preserving the raw transcript for display.
 */

export function normalizeTranscript(rawText) {
  if (!rawText || typeof rawText !== "string") return "";
  let text = rawText;

  // 1. Spaced / punctuated acronyms (e.g. "o t p", "o.t.p", "c v v", "p i n")
  text = text.replace(/\b[oO][\s.-]+[tT][\s.-]+[pP]\b/g, "OTP");
  text = text.replace(/\b[aA][\s.-]+[tT][\s.-]+[pP]\b/g, "OTP");
  text = text.replace(/\b[cC][\s.-]+[vV][\s.-]+[vV]\b/g, "CVV");
  text = text.replace(/\b[pP][\s.-]+[iI][\s.-]+[nN]\b/g, "PIN");
  text = text.replace(/\b[uU][\s.-]+[pP][\s.-]+[iI]\b/g, "UPI");
  text = text.replace(/\b[kK][\s.-]+[yY][\s.-]+[cC]\b/g, "KYC");

  // 2. Contextual ATP -> OTP substitution
  // Only replace "ATP" when accompanied by credential / transaction verbs or cues
  const atpWithVerbBefore = /\b(tell|give|share|send|enter|provide|say|read|received?|got|input|sms|message|code|verify|verification|bank|account|security|6[- ]digit)\b[\w\s]{0,35}\b(atp)\b/gi;
  const atpWithVerbAfter = /\b(atp)\b[\w\s]{0,35}\b(tell|give|share|send|enter|provide|received?|code|sms|number|digits?|verification|immediately|now)\b/gi;

  if (atpWithVerbBefore.test(text) || atpWithVerbAfter.test(text)) {
    text = text.replace(/\b(atp)\b/gi, "OTP");
  }

  // 3. Spelled out variations
  text = text.replace(/\bone[- ]time\s*pass(?:word)?\b/gi, "OTP");
  text = text.replace(/\bpass\s+word\b/gi, "password");
  text = text.replace(/\bnet\s+banking\b/gi, "netbanking");
  text = text.replace(/\bcredit\s+card\b/gi, "credit card");
  text = text.replace(/\bdebit\s+card\b/gi, "debit card");
  text = text.replace(/\bbank\s+account\b/gi, "bank account");
  text = text.replace(/\bdigital\s+arrest\b/gi, "digital arrest");

  return text;
}
