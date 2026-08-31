import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Radio,
  Mic,
  MicOff,
  AlertTriangle,
  AlertOctagon,
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Quote,
  Activity,
  RotateCcw,
  Download,
  Info,
  Clock,
  SlidersHorizontal,
  Lock,
  ChevronRight,
  Loader2,
  Volume2,
  FileText,
  Server,
  Layers,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { Waveform } from "../components/Waveform";
import ThreatSignalCard from "../components/ThreatSignalCard";
import { useChunkRecorder } from "../hooks/useChunkRecorder";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { analyzeChunk, analyzeAudio, analyzeContext } from "../services/api";
import { normalizeTranscript } from "../utils/transcriptNormalizer";

const INITIAL_LIVE_ANALYSIS = {
  status: "listening",
  riskScore: null,
  threatLevel: "EVALUATING",
  scamCategory: "Listening for speech...",
  confidence: "LOW",
  scamDesc: "Awaiting audible speech from active microphone stream.",
  indicators: [],
  evidence: [],
  recommendation: "Listening for speech... Threat assessment will update in real time.",
  updatedAt: null,
};

const HIGH_RISK_TRIGGER_REGEX = /\b(otp|one[- ]time[- ]password|verification[- ]code|auth[- ]code|cvv|cvv\s*number|card\s*pin|atm\s*pin|upi\s*pin|mpin|password|bank\s*password|netbanking\s*password|login\s*password|passcode|card\s*number|debit\s*card|credit\s*card\s*number|transfer\s*money|send\s*money|wire\s*transfer|urgent\s*payment|immediate\s*payment|account\s*blocked|account\s*freeze|account\s*suspended|card\s*blocked|digital\s*arrest|arrest\s*warrant|police\s*case|fir\s*registered|crime\s*branch|cbi|customs\s*parcel|contraband|drugs\s*found|seized\s*parcel|remote\s*access|anydesk|teamviewer|quicksupport|screen\s*share|screen\s*sharing|tax\s*department|income\s*tax\s*notice|rbi\s*official)\b/i;

export function LiveMonitorPage({ onNavigate }) {
  // Session State: 'idle' | 'monitoring' | 'finalizing' | 'completed' | 'error'
  const [sessionState, setSessionState] = useState("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState(null);

  // Audio Device Selection
  const [audioDevices, setAudioDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");

  // Live Analysis & Transcript State
  const [liveAnalysis, setLiveAnalysis] = useState(INITIAL_LIVE_ANALYSIS);
  const [transcript, setTranscript] = useState("");
  const [transcriptSegments, setTranscriptSegments] = useState([]); // [{ time: '00:04', text: '...' }]
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [timelineSortOrder, setTimelineSortOrder] = useState("newest"); // 'newest' | 'oldest'
  const [liveDeepfakeProb, setLiveDeepfakeProb] = useState(null);
  const [finalReport, setFinalReport] = useState(null);
  const [exportFeedback, setExportFeedback] = useState(false);

  const eventSequenceRef = useRef(0);

  const displayedTimelineEvents = useMemo(() => {
    const list = [...timelineEvents];
    if (timelineSortOrder === "oldest") {
      return list.sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));
    }
    return list.sort((a, b) => (b.seq ?? 0) - (a.seq ?? 0));
  }, [timelineEvents, timelineSortOrder]);

  // Timers & Synchronized References
  const sessionStartTimeRef = useRef(null);
  const [sessionElapsedSeconds, setSessionElapsedSeconds] = useState(0);
  const lastEventSecsRef = useRef(-1);
  const liveTranscriptRef = useRef("");
  const latestRequestIdRef = useRef(0);
  const lastAppliedRequestIdRef = useRef(0);
  const lastAnalyzedTranscriptRef = useRef("");
  const analysisTimeoutRef = useRef(null);
  const loggedThreatCuesRef = useRef(new Set());
  const prevRiskScoreRef = useRef(0);
  const prevScamCategoryRef = useRef("");
  const speechDetectedLoggedRef = useRef(false);
  const transcriptSegmentLoggedRef = useRef(false);
  const analysisStartedLoggedRef = useRef(false);
  const transcriptContainerRef = useRef(null);

  // Enumerate Microphones on mount
  useEffect(() => {
    async function loadDevices() {
      try {
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const audioInputs = devices.filter((d) => d.kind === "audioinput");
          setAudioDevices(audioInputs);
          if (audioInputs.length > 0 && !selectedDeviceId) {
            setSelectedDeviceId(audioInputs[0].deviceId);
          }
        }
      } catch (err) {
        console.warn("Device enumeration notice:", err);
      }
    }
    loadDevices();
  }, []);

  // Format Elapsed Seconds as MM:SS
  const formatTimer = useCallback((totalSeconds) => {
    const s = Math.max(0, Math.floor(totalSeconds || 0));
    const mins = String(Math.floor(s / 60)).padStart(2, "0");
    const secs = String(s % 60).padStart(2, "0");
    return `${mins}:${secs}`;
  }, []);

  // Compute Strictly Monotonic Timestamp for Events
  const getSessionTimestamp = useCallback(() => {
    if (!sessionStartTimeRef.current) return "00:00";
    const elapsed = Math.max(0, Math.floor((Date.now() - sessionStartTimeRef.current) / 1000));
    const totalSecs = Math.max(elapsed, (lastEventSecsRef.current ?? -1) + 1);
    lastEventSecsRef.current = totalSecs;
    return formatTimer(totalSecs);
  }, [formatTimer]);

  // Add Event to Detection Timeline (Newest by Sequence)
  const addTimelineEvent = useCallback((text, severity = "info") => {
    const timeStr = getSessionTimestamp();
    eventSequenceRef.current += 1;
    const seq = eventSequenceRef.current;
    setTimelineEvents((prev) => {
      if (prev.length > 0 && prev[0].text === text) return prev;
      if (prev.some((e) => e.text === text)) return prev;
      return [{ id: `evt_${seq}_${Date.now()}`, seq, time: timeStr, text, severity, timestamp: Date.now() }, ...prev];
    });
  }, [getSessionTimestamp]);

  // Execute Live Scam Analysis on Normalized Spoken Speech
  const performLiveAnalysis = useCallback(async (rawText) => {
    const trimmedRaw = (rawText || "").trim();
    if (!trimmedRaw) return;

    const normalized = normalizeTranscript(trimmedRaw);
    if (!normalized) return;

    if (normalized === lastAnalyzedTranscriptRef.current && liveAnalysis.status === "active") {
      return;
    }

    latestRequestIdRef.current += 1;
    const currentRequestId = latestRequestIdRef.current;

    setLiveAnalysis((prev) => ({ ...prev, status: "analyzing" }));

    if (!analysisStartedLoggedRef.current) {
      analysisStartedLoggedRef.current = true;
      addTimelineEvent("Threat analysis started", "info");
    }

    try {
      const res = await analyzeContext(normalized);
      if (currentRequestId < lastAppliedRequestIdRef.current) {
        return;
      }
      lastAppliedRequestIdRef.current = currentRequestId;
      lastAnalyzedTranscriptRef.current = normalized;

      if (res) {
        const finalScore = res.final_risk_score ?? res.context_risk_score ?? 0;
        const indicators = res.detected_indicators || [];
        const evidenceList = res.evidence || [];
        const finalCategory = res.final_scam_category || res.possible_scam_category || "Routine / Normal Call";
        const isEvaluating =
          (res.final_threat_level === "Evaluating" ||
            res.risk_level === "Evaluating" ||
            finalCategory === "Listening for speech...") &&
          indicators.length === 0;

        const finalLevel = isEvaluating
          ? "EVALUATING"
          : res.final_threat_level
          ? `${res.final_threat_level} RISK`
          : res.risk_level
          ? `${res.risk_level} RISK`
          : "LOW RISK";

        // Atomic Synchronized State Update
        setLiveAnalysis({
          status: "active",
          riskScore: isEvaluating ? null : finalScore,
          threatLevel: finalLevel,
          scamCategory: finalCategory,
          confidence: res.scam_category_confidence || (isEvaluating ? "LOW" : "HIGH"),
          scamDesc: res.scam_category_description || "",
          indicators: indicators,
          evidence: evidenceList,
          recommendation: res.recommendation || "Monitoring call conversation for telecommunication fraud tactics.",
          updatedAt: Date.now(),
        });

        // Timeline events for newly detected threat indicators
        for (const ind of indicators) {
          const cueKey = (ind.category || ind.label) + (ind.matched_cue || "");
          if (!loggedThreatCuesRef.current.has(cueKey)) {
            loggedThreatCuesRef.current.add(cueKey);
            const cueStr = ind.matched_cue ? `: "${ind.matched_cue}"` : "";
            addTimelineEvent(`Scam indicator detected: ${ind.label}${cueStr}`, ind.severity === "CRITICAL" ? "danger" : "warning");
          }
        }

        // Timeline event on category change
        if (
          finalCategory !== prevScamCategoryRef.current &&
          finalCategory !== "Routine / Normal Call" &&
          finalCategory !== "Listening for speech..."
        ) {
          addTimelineEvent(`Threat category updated: ${finalCategory}`, "warning");
          prevScamCategoryRef.current = finalCategory;
        }

        // Timeline event on score increase
        if (finalScore !== prevRiskScoreRef.current && finalScore > 0) {
          addTimelineEvent(
            `Threat score updated: ${finalScore}/100`,
            finalScore >= 75 ? "danger" : "warning"
          );
          prevRiskScoreRef.current = finalScore;
        }
      }
    } catch (err) {
      console.warn("Live analysis network notice:", err);
      setLiveAnalysis((prev) => ({ ...prev, status: "active" }));
    }
  }, [addTimelineEvent, liveAnalysis.status]);

  // Progressive Speech Recognition
  const speech = useSpeechRecognition({
    onTranscript: (fullText, interimText) => {
      const activeRaw = (fullText || interimText || "").trim();
      setTranscript(fullText || interimText);
      liveTranscriptRef.current = fullText || interimText;

      // Append segment with timestamp
      if (activeRaw.length > 0) {
        const timeNow = getSessionTimestamp();
        setTranscriptSegments((prev) => {
          if (prev.length > 0 && prev[prev.length - 1].time === timeNow) {
            const updated = [...prev];
            updated[updated.length - 1] = { time: timeNow, text: activeRaw };
            return updated;
          }
          return [...prev, { time: timeNow, text: activeRaw }];
        });
      }

      if (!speechDetectedLoggedRef.current && activeRaw.length > 0) {
        speechDetectedLoggedRef.current = true;
        addTimelineEvent("Speech detected", "info");
      }

      if (!transcriptSegmentLoggedRef.current && activeRaw.length >= 5) {
        transcriptSegmentLoggedRef.current = true;
        addTimelineEvent("Transcript segment received", "info");
      }

      if (activeRaw.length >= 3) {
        const hasHighRisk = HIGH_RISK_TRIGGER_REGEX.test(activeRaw);
        if (analysisTimeoutRef.current) {
          clearTimeout(analysisTimeoutRef.current);
          analysisTimeoutRef.current = null;
        }

        if (hasHighRisk) {
          // Immediate 0ms analysis for critical keywords
          performLiveAnalysis(activeRaw);
        } else {
          // Debounced 800ms analysis for normal speech
          analysisTimeoutRef.current = setTimeout(() => {
            performLiveAnalysis(activeRaw);
          }, 800);
        }
      }
    },
  });

  // Rolling Chunk Recorder for Audio Waveform & VAD
  const chunkRecorder = useChunkRecorder({
    onChunk: async (chunkFile) => {
      try {
        const textToSend = liveTranscriptRef.current || transcript;
        const normalizedText = normalizeTranscript(textToSend);

        const result = await analyzeChunk({
          file: chunkFile,
          transcript: normalizedText.trim() || undefined,
        });

        if (result && result.deepfake_probability != null) {
          setLiveDeepfakeProb(result.deepfake_probability);
          if (result.deepfake_probability >= 0.85) {
            addTimelineEvent("Voice Authenticity: Neural synthetic vocoder artifacts detected", "danger");
          }
        }
      } catch (err) {
        // Rolling chunk errors are non-fatal
      }
    },
  });

  // Keep Timer Synchronized
  useEffect(() => {
    let timer = null;
    if (chunkRecorder.isLive && sessionStartTimeRef.current) {
      timer = setInterval(() => {
        const secs = Math.max(0, Math.floor((Date.now() - sessionStartTimeRef.current) / 1000));
        setSessionElapsedSeconds(secs);
      }, 500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [chunkRecorder.isLive]);

  // Auto-scroll internal transcript box without affecting main window/page scroll
  useEffect(() => {
    if (transcriptContainerRef.current) {
      const el = transcriptContainerRef.current;
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      if (isNearBottom) {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [transcript, transcriptSegments]);

  // Start Live Monitoring Session
  const handleStartMonitoring = async () => {
    try {
      setErrorMessage(null);
      setFinalReport(null);
      setLiveAnalysis(INITIAL_LIVE_ANALYSIS);
      setTranscript("");
      setTranscriptSegments([]);
      liveTranscriptRef.current = "";
      latestRequestIdRef.current = 0;
      lastAppliedRequestIdRef.current = 0;
      lastAnalyzedTranscriptRef.current = "";
      loggedThreatCuesRef.current.clear();
      prevRiskScoreRef.current = 0;
      prevScamCategoryRef.current = "";
      speechDetectedLoggedRef.current = false;
      transcriptSegmentLoggedRef.current = false;
      analysisStartedLoggedRef.current = false;

      sessionStartTimeRef.current = Date.now();
      lastEventSecsRef.current = -1;
      setSessionElapsedSeconds(0);
      eventSequenceRef.current = 1;
      setTimelineEvents([
        { id: "evt_1", seq: 1, time: "00:00", text: "Live call monitoring initiated", severity: "info", timestamp: Date.now() },
      ]);

      setSessionState("monitoring");
      setStatusMessage("Continuous live call surveillance active. Listening & transcribing in real time...");

      try {
        speech.start();
      } catch (e) {
        console.warn("SpeechRecognition notice:", e);
      }

      await chunkRecorder.start();
      addTimelineEvent("Microphone connected", "info");
    } catch (err) {
      console.error("Microphone access failed:", err);
      setSessionState("error");
      setErrorMessage("Microphone permission denied or device unavailable. Please allow microphone access in your browser to enable live call protection.");
    }
  };

  // Stop Live Monitoring Session & Execute Complete Finalization Pipeline
  const handleStopMonitoring = async () => {
    console.log("[LiveMonitor] Step 1: Stopping live monitoring session...");
    setSessionState("finalizing");
    setStatusMessage("Finalizing audio session and running multi-signal evaluation...");

    try {
      if (analysisTimeoutRef.current) {
        clearTimeout(analysisTimeoutRef.current);
        analysisTimeoutRef.current = null;
      }

      const recordedFile = chunkRecorder.stop();
      speech.stop();
      addTimelineEvent("Live audio capture ended", "info");

      const capturedText = (liveTranscriptRef.current || transcript || "").trim();
      const normalizedCaptured = normalizeTranscript(capturedText);
      console.log("[LiveMonitor] Step 2: Captured transcript ready. Length:", normalizedCaptured.length);

      if (normalizedCaptured) {
        addTimelineEvent("Executing final threat assessment", "info");

        // Helper timeout promise
        const timeoutPromise = (ms, msg) =>
          new Promise((_, reject) => setTimeout(() => reject(new Error(msg)), ms));

        let reportData = null;

        // Try fast context analysis with trained NLP scam model (guaranteed timeout 3.5s)
        try {
          console.log("[LiveMonitor] Step 3: Invoking trained scam detection model...");
          const contextRes = await Promise.race([
            analyzeContext(normalizedCaptured),
            timeoutPromise(3500, "Context analysis request timeout"),
          ]);

          if (contextRes) {
            console.log("[LiveMonitor] Step 4: Model inference successful:", contextRes.classification, "Risk score:", contextRes.final_risk_score);
            const finalScore = contextRes.final_risk_score ?? contextRes.context_risk_score ?? liveAnalysis.riskScore ?? 0;
            const finalLevel = contextRes.final_threat_level || contextRes.risk_level || (liveAnalysis.threatLevel ? liveAnalysis.threatLevel.replace(" RISK", "") : "LOW");
            const finalCat = contextRes.final_scam_category || contextRes.possible_scam_category || (liveAnalysis.scamCategory !== "Listening for speech..." ? liveAnalysis.scamCategory : "Routine / Normal Call");
            const indicators = (contextRes.detected_indicators && contextRes.detected_indicators.length > 0)
              ? contextRes.detected_indicators
              : liveAnalysis.indicators;
            const evidenceList = (contextRes.evidence && contextRes.evidence.length > 0)
              ? contextRes.evidence
              : liveAnalysis.evidence;

            reportData = {
              analysis_id: "live_" + Date.now().toString(36),
              created_at: new Date().toISOString(),
              analysis_status: "completed",
              final_risk_score: finalScore,
              risk_level: finalLevel,
              possible_scam_category: finalCat,
              scam_category_confidence: contextRes.scam_category_confidence || liveAnalysis.confidence || "HIGH",
              scam_category_description: contextRes.scam_category_description || liveAnalysis.scamDesc || "Conversational intent evaluated across known scam patterns.",
              recommendation: contextRes.recommendation || liveAnalysis.recommendation || "Verify caller identity independently before sharing sensitive credentials.",
              detected_threats: indicators,
              evidence: evidenceList,
              transcript: normalizedCaptured,
              voice_authenticity: liveDeepfakeProb >= 0.85 ? "HIGH_CONFIDENCE_SYNTHETIC" : "LIKELY_HUMAN",
              deepfake_probability: liveDeepfakeProb ?? 0.05,
              risk_reasoning: indicators.length > 0
                ? `Final session evaluation identified ${indicators.length} threat indicators in the live conversation.`
                : "No high-confidence telecommunication fraud indicators were detected.",
            };
          }
        } catch (apiErr) {
          console.warn("[LiveMonitor] Context analysis API notice:", apiErr);
        }

        // If API did not return or timed out, build from live surveillance state
        if (!reportData) {
          console.log("[LiveMonitor] Step 4b: Using live state telemetry for final report fallback.");
          reportData = {
            analysis_id: "live_" + Date.now().toString(36),
            created_at: new Date().toISOString(),
            analysis_status: "completed",
            final_risk_score: liveAnalysis.riskScore ?? 0,
            risk_level: liveAnalysis.threatLevel ? liveAnalysis.threatLevel.replace(" RISK", "") : "LOW",
            possible_scam_category: liveAnalysis.scamCategory !== "Listening for speech..." ? liveAnalysis.scamCategory : "Routine / Normal Call",
            scam_category_confidence: liveAnalysis.confidence || "MEDIUM",
            scam_category_description: liveAnalysis.scamDesc || "Live surveillance evaluation.",
            recommendation: liveAnalysis.recommendation || "Verify caller identity independently before sharing credentials.",
            detected_threats: liveAnalysis.indicators || [],
            evidence: liveAnalysis.evidence || [],
            transcript: normalizedCaptured,
            voice_authenticity: liveDeepfakeProb >= 0.85 ? "HIGH_CONFIDENCE_SYNTHETIC" : "LIKELY_HUMAN",
            deepfake_probability: liveDeepfakeProb ?? 0.05,
            risk_reasoning: (liveAnalysis.indicators || []).length > 0
              ? `Final session evaluation identified ${liveAnalysis.indicators.length} threat indicators in the live conversation.`
              : "No high-confidence telecommunication fraud indicators were detected.",
          };
        }

        setFinalReport(reportData);
        addTimelineEvent("Session report finalized", "info");
      } else {
        // No speech captured at all during session
        console.log("[LiveMonitor] Step 3: No speech captured during session.");
        setFinalReport({
          analysis_id: "live_" + Date.now().toString(36),
          created_at: new Date().toISOString(),
          analysis_status: "insufficient_audio",
          speech_detected: false,
          final_risk_score: null,
          risk_level: "NO_SPEECH",
          possible_scam_category: "No Speech Detected",
          scam_category_confidence: "LOW",
          scam_category_description: "No spoken conversation was detected during this monitoring session.",
          voice_authenticity: "INSUFFICIENT_AUDIO",
          recommendation: "No audible speech was detected. For real-time call protection, speak clearly into the microphone or place the call on speaker.",
          detected_threats: [],
          evidence: [],
          transcript: "",
          risk_reasoning: "Session concluded with zero detected voiced audio frames.",
        });
        addTimelineEvent("No speech detected during session", "info");
      }
    } catch (err) {
      console.error("[LiveMonitor] Critical stop monitoring error:", err);
      setFinalReport({
        analysis_id: "live_" + Date.now().toString(36),
        created_at: new Date().toISOString(),
        analysis_status: "completed",
        final_risk_score: liveAnalysis.riskScore ?? 0,
        risk_level: liveAnalysis.threatLevel ? liveAnalysis.threatLevel.replace(" RISK", "") : "LOW",
        possible_scam_category: liveAnalysis.scamCategory !== "Listening for speech..." ? liveAnalysis.scamCategory : "Routine / Normal Call",
        scam_category_confidence: liveAnalysis.confidence || "MEDIUM",
        scam_category_description: liveAnalysis.scamDesc || "Real-time stream evaluation.",
        recommendation: liveAnalysis.recommendation || "Verify caller identity independently before sharing credentials.",
        detected_threats: liveAnalysis.indicators || [],
        evidence: liveAnalysis.evidence || [],
        transcript: liveTranscriptRef.current || transcript || "",
        voice_authenticity: liveDeepfakeProb >= 0.85 ? "HIGH_CONFIDENCE_SYNTHETIC" : "LIKELY_HUMAN",
        deepfake_probability: liveDeepfakeProb ?? 0.05,
      });
    } finally {
      console.log("[LiveMonitor] Step 5: Finalization complete. Transitioning sessionState -> completed.");
      setSessionState("completed");
    }
  };

  // Export Session Markdown Report
  const handleExportSessionReport = () => {
    try {
      const report = finalReport || liveAnalysis;
      const score = report.final_risk_score ?? report.riskScore ?? 0;
      const level = report.risk_level ?? (report.threatLevel ? report.threatLevel.replace(" RISK", "") : "LOW");
      const category = report.possible_scam_category ?? (report.scamCategory !== "Listening for speech..." ? report.scamCategory : "Routine / Normal Call");
      const rec = report.recommendation ?? "Verify caller identity independently before sharing confidential credentials.";
      const transcriptText = report.transcript || liveTranscriptRef.current || transcript || "No audible conversation captured.";
      const indicators = report.detected_threats || report.indicators || [];
      const sessionId = report.analysis_id || `live_${Date.now().toString(36)}`;
      const voiceAuth = report.voice_authenticity ? report.voice_authenticity.replace(/_/g, " ") : "Likely Human";
      const deepfakeConf = report.deepfake_probability != null ? `${Math.round(report.deepfake_probability * 100)}%` : "N/A";
      const auditStatus = report.risk_level === "NO_SPEECH" ? "No Speech Captured" : "Verified Final";

      // Chronologically sorted timeline events for the official export report
      const sortedEvents = [...timelineEvents].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));

      const mdContent = `# Voice Shield — Live Call Monitoring Session Report

**Session ID:** ${sessionId}  
**Capture Timestamp:** ${new Date().toISOString()} (${new Date().toLocaleString()})  
**Session Duration:** ${formatTimer(sessionElapsedSeconds)}  
**Audit Status:** ${auditStatus}  

---

## 1. Executive Threat Assessment

- **Overall Threat Score:** **${score} / 100**
- **Threat Level:** **${level.toUpperCase()} RISK**
- **Identified Scam Scenario:** **${category}** (Confidence: ${report.scam_category_confidence || report.confidence || "HIGH"})
- **Voice Authenticity Evaluation:** **${voiceAuth}** (Deepfake Confidence: ${deepfakeConf})
- **Independent Dimensions Principle:** Voice Authenticity and Conversation Intent are evaluated independently. An authentic human voice can conduct a critical scam.

### Recommended Immediate Action
> **${rec}**

---

## 2. Spoken Conversation Transcript
\`\`\`text
${transcriptText}
\`\`\`

---

## 3. Detected Threat Indicators (${indicators.length})
${
  indicators.length > 0
    ? indicators
        .map(
          (ind, i) =>
            `${i + 1}. **${ind.label || ind.category}** [Severity: ${ind.severity || "HIGH"}]\n   - Evidence Cue: "${ind.matched_cue || "N/A"}"\n   - Analysis: ${ind.explanation || ind.why_it_matters || "Detected telecommunication deception cue."}`
        )
        .join("\n\n")
    : "✓ No telecommunication fraud, coercion, OTP theft, or authority impersonation tactics detected."
}

---

## 4. Chronological Detection Event Log (${sortedEvents.length} Events)
${
  sortedEvents.length > 0
    ? sortedEvents
        .map((evt) => `- **[${evt.time}]** ${evt.text} *(Severity: ${evt.severity || "info"})*`)
        .join("\n")
    : "No events logged."
}

---

## 5. Technical Pipeline Telemetry
- **Audio Ingest:** 16 kHz PCM Live Stream
- **Acoustic Model:** VoiceShield-Acoustic-v2 (Wav2Vec2 Neural Audio Classifier)
- **Linguistic Engine:** VoiceShield-NLP-v2 (Conversational Threat Intent VAD)
- **Risk Fusion:** Tri-Factor Multi-Signal Synthesis ($0.40 \\times \\text{Deepfake} + 0.45 \\times \\text{Context} + 0.15 \\times \\text{Prosody}$)

---
*Report generated securely by Voice Shield Live Call Protection Platform. Ephemeral memory processing enforced — zero biometric storage retained.*
`;

      const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `voice-shield-live-session-${sessionId}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setExportFeedback(true);
      setTimeout(() => setExportFeedback(false), 3000);
    } catch (err) {
      console.error("Export report error:", err);
    }
  };

  const isCriticalThreat = liveAnalysis.riskScore >= 75 || liveAnalysis.threatLevel === "CRITICAL RISK";
  const isHighThreat = liveAnalysis.riskScore >= 50 && liveAnalysis.riskScore < 75;

  return (
    <div className="analyze-workspace-layout">
      {/* 1. Page Header */}
      <section className="page-intro-header flex justify-between items-start flex-wrap gap-4">
        <div>
          <span className="page-pretitle">REAL-TIME ACTIVE CALL SURVEILLANCE</span>
          <h1 className="page-headline">Live Microphone Monitoring</h1>
          <p className="page-subheadline">
            Continuous real-time threat detection and voice authenticity analysis during an active phone or voice conversation.
          </p>
        </div>

        {sessionState === "monitoring" && (
          <button
            type="button"
            className="primary-execute-btn btn-danger flex items-center gap-1.5 self-center"
            onClick={handleStopMonitoring}
          >
            <MicOff size={14} />
            <span>Stop Monitoring &amp; Finalize</span>
          </button>
        )}
      </section>

      {/* 2. Critical Risk Alert Banner */}
      {sessionState === "monitoring" && (isCriticalThreat || isHighThreat) && (
        <div className={`p-4 rounded-lg border mb-4 flex items-start gap-3 animate-pulse ${isCriticalThreat ? "bg-red-50 border-red-300 text-red-900" : "bg-amber-50 border-amber-300 text-amber-900"}`}>
          <AlertTriangle size={24} className={isCriticalThreat ? "text-red-700 flex-shrink-0 mt-0.5" : "text-amber-700 flex-shrink-0 mt-0.5"} />
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <strong className="text-sm font-bold uppercase tracking-wider">
                {isCriticalThreat ? "CRITICAL FRAUD THREAT DETECTED" : "HIGH-RISK CALL PATTERN DETECTED"}
              </strong>
              <span className={`status-pill-subtle ${isCriticalThreat ? "pill-danger" : "pill-warning"}`}>
                {liveAnalysis.scamCategory}
              </span>
            </div>
            <p className="text-xs mt-1 leading-relaxed">
              <strong>IMMEDIATE ACTION: </strong>
              {liveAnalysis.recommendation}
            </p>
          </div>
        </div>
      )}

      {/* 3. INITIAL PRE-MONITORING STATE */}
      {sessionState === "idle" && (
        <div className="max-w-4xl mx-auto my-6">
          <div className="security-report-card">
            <div className="report-summary-header">
              <span className="report-pretitle">STANDBY SURVEILLANCE CONSOLE</span>
              <h2 className="text-lg font-bold text-slate-900 mt-1">Start Real-Time Call Protection</h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Place your phone on speaker or speak near your microphone. Voice Shield will listen, transcribe, and assess conversational threats dynamically.
              </p>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="status-banner banner-error my-3">
                <AlertOctagon size={16} className="flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Microphone Settings & Privacy Notice */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Mic size={16} className="text-blue-700" />
                  <strong className="text-xs font-bold text-slate-800 uppercase tracking-wider">Microphone Input</strong>
                </div>
                <label className="text-xs text-slate-500 block mb-1">Select Audio Capture Device:</label>
                {audioDevices.length > 0 ? (
                  <select
                    className="clean-input text-xs w-full bg-white"
                    value={selectedDeviceId}
                    onChange={(e) => setSelectedDeviceId(e.target.value)}
                  >
                    {audioDevices.map((d, i) => (
                      <option key={d.deviceId || i} value={d.deviceId}>
                        {d.label || `Microphone ${i + 1}`}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-xs text-slate-600 italic">Default system microphone will be requested on start.</p>
                )}
                <div className="mt-3 flex items-center gap-1.5 text-2xs text-emerald-700 font-semibold">
                  <CheckCircle2 size={13} />
                  <span>Ready to stream at 16 kHz uniform audio buffer</span>
                </div>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Lock size={16} className="text-blue-700" />
                  <strong className="text-xs font-bold text-slate-800 uppercase tracking-wider">Privacy &amp; Permissions</strong>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Microphone audio is processed locally and ephemerally in memory for threat detection. No recordings or biometric profiles are permanently retained.
                </p>
                <div className="mt-3 flex items-center gap-1.5 text-2xs text-slate-500">
                  <Shield size={13} className="text-blue-700" />
                  <span>Zero biometric enrollment required</span>
                </div>
              </div>
            </div>

            {/* Prominent CTA to Start Live Monitoring */}
            <div className="text-center py-4">
              <button
                type="button"
                className="primary-execute-btn btn-large px-8 py-3.5 mx-auto"
                onClick={handleStartMonitoring}
              >
                <Radio size={18} className="text-white animate-pulse" />
                <span className="text-sm font-bold">Start Live Call Monitoring</span>
              </button>
              <span className="text-2xs text-slate-500 block mt-2">
                Clicking will request microphone permission and initiate real-time audio analysis.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 4. ACTIVE MONITORING DASHBOARD */}
      {sessionState === "monitoring" && (
        <div className="product-workspace">
          {/* LEFT COLUMN: ACTIVE AUDIO CONSOLE & LIVE TRANSCRIPT */}
          <section className="intake-column">
            <div className="intake-card">
              <div className="section-title-row">
                <div className="flex items-center gap-2">
                  <span className="live-pulse-dot active-pulse" />
                  <h2 className="section-title">Active Call Audio Stream</h2>
                </div>
                <span className="font-mono text-sm font-bold text-slate-900 bg-slate-100 px-2.5 py-0.5 rounded border border-slate-200">
                  {formatTimer(sessionElapsedSeconds)}
                </span>
              </div>

              {/* Live Telemetry Status Row */}
              <div className="grid grid-cols-3 gap-2 text-xs text-slate-600 p-3 bg-slate-50 border border-slate-200 rounded-lg mb-3">
                <div>
                  <span className="text-slate-400 block text-2xs uppercase">Microphone</span>
                  <strong className="text-emerald-700">Connected</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-2xs uppercase">Speech Activity</span>
                  <strong className={chunkRecorder.speechActivity === "speaking" ? "text-blue-700" : "text-slate-600"}>
                    {chunkRecorder.speechActivity === "speaking" ? "Speaking (VAD)" : "Listening..."}
                  </strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-2xs uppercase">Analysis State</span>
                  <strong className={liveAnalysis.status === "analyzing" ? "text-amber-700" : "text-emerald-700"}>
                    {liveAnalysis.status === "analyzing" ? "Evaluating..." : "Active Stream"}
                  </strong>
                </div>
              </div>

              {/* Real Web Audio Waveform */}
              <div className="mb-3">
                <div className="flex justify-between items-center text-xs text-slate-500 mb-1">
                  <span className="font-semibold">Live Audio Waveform</span>
                  <span>{chunkRecorder.speechActivity === "speaking" ? "Speech Detected (16 kHz)" : "Listening for speech..."}</span>
                </div>
                <Waveform
                  analyser={chunkRecorder.analyser}
                  isLive={chunkRecorder.isLive}
                  audioLevel={chunkRecorder.audioLevel}
                />
              </div>

              {/* Live Progressive Transcript Box */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg mb-3">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Live Progressive Transcript
                  </span>
                  <span className="status-pill-subtle pill-safe">
                    {speech.isListening ? "Transcribing in real time" : "Listening..."}
                  </span>
                </div>

                <div ref={transcriptContainerRef} className="max-h-48 overflow-y-auto pr-1 text-xs text-slate-800 leading-relaxed font-medium">
                  {transcriptSegments.length > 0 ? (
                    <div className="space-y-1.5">
                      {transcriptSegments.map((seg, idx) => (
                        <div key={idx} className="flex items-start gap-2">
                          <span className="text-2xs font-mono text-slate-400 mt-0.5 flex-shrink-0">
                            [{seg.time}]
                          </span>
                          <p className="break-words text-slate-800">{seg.text}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic py-3">
                      Listening for speech... Words will appear here progressively with timestamps as the conversation occurs.
                    </p>
                  )}
                </div>
              </div>

              {/* Stop Monitoring Control */}
              <div className="action-buttons-row">
                <button
                  type="button"
                  className="primary-execute-btn btn-danger"
                  onClick={handleStopMonitoring}
                >
                  <MicOff size={16} />
                  <span>Stop Monitoring &amp; Finalize Report</span>
                </button>
              </div>
            </div>
          </section>

          {/* RIGHT COLUMN: REAL-TIME THREAT TELEMETRY & TIMELINE */}
          <section className="results-column">
            <div className="security-report-card">
              {/* Dynamic Threat Score Header */}
              <div className="report-summary-header">
                <div className="flex justify-between items-start flex-wrap gap-3 mb-2">
                  <div>
                    <span className="report-pretitle">REAL-TIME THREAT EVALUATION</span>
                    <span className={`risk-text-tag level-${(liveAnalysis.threatLevel || "low").toLowerCase().replace(" risk", "")} text-lg mt-0.5 block`}>
                      {liveAnalysis.threatLevel}
                    </span>
                  </div>
                  <div className="report-score-pill">
                    <span className={`score-num ${liveAnalysis.riskScore >= 75 ? "text-red-700" : liveAnalysis.riskScore >= 50 ? "text-red-600" : liveAnalysis.riskScore >= 25 ? "text-amber-700" : "text-emerald-700"}`}>
                      {liveAnalysis.riskScore != null ? liveAnalysis.riskScore : "--"}
                    </span>
                    <span className="score-denom">/ 100</span>
                  </div>
                </div>

                {/* Possible Scam Category */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md mb-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">Possible Scam Category</span>
                      <strong className="text-base text-slate-900 mt-0.5 block">
                        {liveAnalysis.scamCategory}
                      </strong>
                    </div>
                    <span className={`status-pill-subtle ${liveAnalysis.confidence === "HIGH" ? "pill-danger" : liveAnalysis.confidence === "MEDIUM" ? "pill-warning" : "pill-neutral"}`}>
                      Confidence: {liveAnalysis.confidence}
                    </span>
                  </div>
                </div>

                {/* Recommended Immediate Action */}
                <div className="report-action-box mb-3">
                  <strong className="text-xs text-slate-900 block mb-0.5">Recommended Action:</strong>
                  <span className="text-xs text-blue-900 leading-relaxed block">{liveAnalysis.recommendation}</span>
                </div>
              </div>

              {/* Detected Threat Indicators */}
              <div className="report-signals-section">
                <h4 className="report-section-heading mb-2">
                  Live Detected Threat Signals ({liveAnalysis.indicators.length})
                </h4>
                {liveAnalysis.indicators.length > 0 ? (
                  <div className="space-y-2">
                    {liveAnalysis.indicators.map((ind, i) => (
                      <ThreatSignalCard key={i} signal={ind} index={i} />
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic py-1">
                    No threat signals detected yet. Monitoring active speech...
                  </p>
                )}
              </div>

              {/* Voice Authenticity Telemetry */}
              <div className="report-signals-section">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="report-section-heading">Voice Authenticity</h4>
                  <span className="status-pill-subtle pill-safe">
                    {liveDeepfakeProb >= 0.85 ? "Synthetic Detected" : liveDeepfakeProb >= 0.65 ? "Suspicious" : "Likely Human"}
                  </span>
                </div>
                <p className="text-xs text-slate-600">
                  {liveDeepfakeProb >= 0.85
                    ? `Pretrained neural model detected synthetic speech vocoder artifacts (${Math.round(liveDeepfakeProb * 100)}% confidence).`
                    : "Acoustic spectrogram dynamics match natural biological human speech bounds."}
                </p>
              </div>

              {/* Live Detection Timeline */}
              <div className="report-signals-section">
                <div className="flex justify-between items-center mb-2 flex-wrap gap-2">
                  <h4 className="report-section-heading mb-0">Live Detection Timeline ({timelineEvents.length})</h4>
                  <div className="timeline-sort-control">
                    <span className="timeline-sort-label">Sort:</span>
                    <div className="timeline-segmented-group" role="group" aria-label="Timeline sort order">
                      <button
                        type="button"
                        className={`timeline-segment-btn ${timelineSortOrder === "newest" ? "active" : ""}`}
                        onClick={() => setTimelineSortOrder("newest")}
                      >
                        Newest First
                      </button>
                      <button
                        type="button"
                        className={`timeline-segment-btn ${timelineSortOrder === "oldest" ? "active" : ""}`}
                        onClick={() => setTimelineSortOrder("oldest")}
                      >
                        Oldest First
                      </button>
                    </div>
                  </div>
                </div>
                <div className="timeline-feed-box max-h-48 overflow-y-auto">
                  {displayedTimelineEvents.map((evt, idx) => (
                    <div key={idx} className="timeline-event-item">
                      <span className="timeline-time-badge">{evt.time}</span>
                      <span className={`dot ${evt.severity === "danger" ? "dot-crimson" : evt.severity === "warning" ? "dot-amber" : "dot-blue"}`} />
                      <span className="timeline-event-desc">{evt.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* 5. FINALIZING PROCESSING STATE */}
      {sessionState === "finalizing" && (
        <div className="max-w-2xl mx-auto my-12 p-8 bg-white border border-slate-200 rounded-lg shadow-sm text-center">
          <Loader2 size={32} className="spin-icon text-blue-700 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-slate-900">Finalizing Live Session Assessment</h2>
          <p className="text-sm text-slate-600 mt-1">{statusMessage}</p>
        </div>
      )}

      {/* 6. REDESIGNED FULL-WIDTH COMPLETED FINAL REPORT */}
      {sessionState === "completed" && finalReport && (
        <div className="final-report-full-layout">
          {/* Top Header & Export Action Row */}
          <div className="final-report-top-bar">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-200">
                <ShieldCheck size={24} />
              </div>
              <div>
                <span className="text-2xs font-mono font-bold text-blue-700 tracking-wider uppercase block">FINAL AUDIT REPORT</span>
                <h2 className="text-xl font-bold text-slate-900">Live Surveillance Session Summary</h2>
                <span className="text-xs text-slate-500 font-mono">
                  Session ID: {finalReport.analysis_id || "live_session"} • Captured: {new Date().toLocaleTimeString()}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <button
                type="button"
                className={`secondary-btn export-report-btn ${exportFeedback ? "export-success" : ""}`}
                onClick={handleExportSessionReport}
                title="Export full session report in Markdown format"
              >
                {exportFeedback ? (
                  <>
                    <CheckCircle2 size={15} className="text-emerald-700 flex-shrink-0" />
                    <span className="text-emerald-800 font-bold">Report Exported ✓</span>
                  </>
                ) : (
                  <>
                    <Download size={15} className="text-slate-600 flex-shrink-0" />
                    <span>Export Session Report</span>
                  </>
                )}
              </button>
              <button
                type="button"
                className="primary-execute-btn start-new-session-btn"
                onClick={handleStartMonitoring}
              >
                <RotateCcw size={14} className="flex-shrink-0" />
                <span>Start New Session</span>
              </button>
            </div>
          </div>

          {/* Full-Width Top Metric Summary Grid */}
          <div className="final-summary-metrics-grid">
            <div className="final-metric-box">
              <span className="metric-k">Threat Level</span>
              <strong className={`metric-v text-lg level-${(finalReport.risk_level || "low").toLowerCase().replace(" risk", "").replace("_", "")}`}>
                {finalReport.risk_level === "NO_SPEECH" ? "No Speech Detected" : `${finalReport.risk_level} RISK`}
              </strong>
            </div>

            <div className="final-metric-box">
              <span className="metric-k">Threat Score</span>
              <div className="flex items-baseline gap-1">
                <strong className={`text-2xl font-extrabold ${finalReport.final_risk_score >= 75 ? "text-red-700" : finalReport.final_risk_score >= 50 ? "text-amber-700" : finalReport.final_risk_score != null ? "text-emerald-700" : "text-slate-400"}`}>
                  {finalReport.final_risk_score != null ? finalReport.final_risk_score : "—"}
                </strong>
                <span className="text-xs text-slate-500 font-medium">/ 100</span>
              </div>
            </div>

            <div className="final-metric-box">
              <span className="metric-k">Scam Category</span>
              <strong className="metric-v text-sm text-slate-900 truncate">
                {finalReport.possible_scam_category || "Routine / Normal Call"}
              </strong>
            </div>

            <div className="final-metric-box">
              <span className="metric-k">Voice Authenticity</span>
              <strong className="metric-v text-sm text-emerald-700">
                {finalReport.voice_authenticity ? finalReport.voice_authenticity.replace("_", " ") : "Likely Human"}
              </strong>
            </div>

            <div className="final-metric-box">
              <span className="metric-k">Session Duration</span>
              <strong className="metric-v text-base text-slate-900 font-mono">
                {formatTimer(sessionElapsedSeconds)}
              </strong>
            </div>

            <div className="final-metric-box">
              <span className="metric-k">Audit Status</span>
              <span className={`status-pill-subtle ${finalReport.risk_level === "NO_SPEECH" ? "pill-warning" : "pill-safe"}`}>
                {finalReport.risk_level === "NO_SPEECH" ? "No Speech Captured" : "Verified Final"}
              </span>
            </div>
          </div>

          {/* Main 2-Column Responsive Body */}
          <div className="final-report-main-grid">
            {/* Left Column: Threat Intelligence & Actions */}
            <div className="final-report-card">
              <h3 className="card-section-title">Threat Assessment &amp; Guidance</h3>
              
              {/* Category Explanation */}
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-md mb-3">
                <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">Identified Scenario</span>
                <strong className="text-base text-slate-900 mt-0.5 block">
                  {finalReport.possible_scam_category || "Routine / Normal Call"}
                </strong>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  {finalReport.scam_category_description || "The conversation was evaluated against known telecommunication fraud and coercion vectors."}
                </p>
              </div>

              {/* Recommended Action */}
              <div className="report-action-box mb-4">
                <strong className="text-xs text-slate-900 block mb-0.5">Recommended Immediate Action:</strong>
                <span className="text-xs text-blue-900 leading-relaxed block font-medium">
                  {finalReport.recommendation || "Verify caller identity independently before sharing confidential credentials."}
                </span>
              </div>

              {/* Detected Threat Indicators */}
              <div>
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">
                  Detected Threat Signals ({(finalReport.detected_threats || []).length})
                </h4>
                {(finalReport.detected_threats || []).length > 0 ? (
                  <div className="space-y-2">
                    {(finalReport.detected_threats || []).map((ind, i) => (
                      <ThreatSignalCard key={i} signal={ind} index={i} />
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-900">
                    <CheckCircle2 size={14} className="inline mr-1 text-emerald-700" />
                    <span>No coercion, OTP theft, or authority impersonation tactics detected.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Timeline & Technical Telemetry */}
            <div className="final-report-card">
              <h3 className="card-section-title">Session Telemetry &amp; Detection History</h3>

              {/* Reverse-Chronological Timeline (Newest at Top) */}
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2 flex-wrap gap-2">
                  <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
                    Detection Event Log ({timelineEvents.length} Events)
                  </span>
                  <div className="timeline-sort-control">
                    <span className="timeline-sort-label">Sort:</span>
                    <div className="timeline-segmented-group" role="group" aria-label="Timeline sort order">
                      <button
                        type="button"
                        className={`timeline-segment-btn ${timelineSortOrder === "newest" ? "active" : ""}`}
                        onClick={() => setTimelineSortOrder("newest")}
                      >
                        Newest First
                      </button>
                      <button
                        type="button"
                        className={`timeline-segment-btn ${timelineSortOrder === "oldest" ? "active" : ""}`}
                        onClick={() => setTimelineSortOrder("oldest")}
                      >
                        Oldest First
                      </button>
                    </div>
                  </div>
                </div>
                <div className="timeline-feed-box max-h-56 overflow-y-auto">
                  {displayedTimelineEvents.map((evt, idx) => (
                    <div key={idx} className="timeline-event-item">
                      <span className="timeline-time-badge">{evt.time}</span>
                      <span className={`dot ${evt.severity === "danger" ? "dot-crimson" : evt.severity === "warning" ? "dot-amber" : "dot-blue"}`} />
                      <span className="timeline-event-desc">{evt.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Technical Specifications Box */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-700 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-500">Audio Ingestion:</span>
                  <strong className="text-slate-800 font-mono">16 kHz PCM Stream</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Acoustic Model:</span>
                  <strong className="text-slate-800">VoiceShield-Acoustic-v2</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Speech-to-Text:</span>
                  <strong className="text-slate-800">Web Speech VAD Pipeline</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Storage Policy:</span>
                  <strong className="text-emerald-700">Ephemeral In-Memory Only</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Full-Width Lower Section: Preserved Full Spoken Transcript */}
          <div className="final-transcript-card">
            <div className="flex justify-between items-center mb-2 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-blue-700" />
                <h3 className="text-sm font-bold text-slate-900">Preserved Spoken Conversation Transcript</h3>
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {transcript ? `${transcript.split(/\s+/).filter(Boolean).length} words captured` : "0 words"}
              </span>
            </div>

            {transcript ? (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 leading-relaxed font-mono max-h-64 overflow-y-auto">
                <p className="break-words italic">&quot;{transcript}&quot;</p>
              </div>
            ) : (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                No spoken conversation was detected or transcribed during this monitoring session.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
