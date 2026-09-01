import React, { useState, useRef, useEffect } from "react";
import {
  Upload,
  FileAudio,
  FileText,
  Activity,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Shield,
  ShieldAlert,
  Volume2,
  VolumeX,
  RotateCcw,
  Download,
  Trash2,
  Play,
  Pause,
  RefreshCw,
  Quote,
  Sparkles,
  Info,
  Clock,
  Layers,
  ChevronRight,
  Loader2,
  FileCheck,
} from "lucide-react";
import {
  analyzeAudio,
  analyzeContext,
  transcribeAudio,
  getHealth,
  saveAnalysisRecord,
} from "../services/api";
import ThreatSignalCard from "../components/ThreatSignalCard";
import { normalizeTranscript } from "../utils/transcriptNormalizer";

const DEMO_SAMPLES = [
  {
    id: "otp_theft",
    label: "OTP Credential Theft",
    desc: "Active harvesting of one-time password and banking credentials",
    text: "Hello, this is officer Vikram from the bank security department. We noticed an unauthorized transaction of 45,000 rupees on your account. A 6-digit verification OTP has been sent to your registered mobile number. Please tell me the OTP immediately right now so we can block the transaction and freeze the fraudster's account.",
  },
  {
    id: "digital_arrest",
    label: "Digital Arrest Extortion",
    desc: "Impersonation of police / CBI with legal arrest threats",
    text: "This is Inspector Sharma calling from Mumbai Cyber Crime Branch. A DHL courier parcel under your Aadhaar number was intercepted containing illegal narcotics and fake passports. A non-bailable arrest warrant has been registered against you. You are under digital arrest. Do not disconnect this call or you will be arrested in 30 minutes. Transfer the clearance deposit to this RBI verified escrow account immediately.",
  },
  {
    id: "legitimate_support",
    label: "Routine Customer Support",
    desc: "Legitimate customer service without fraud cues",
    text: "Good morning! Thank you for calling CloudTel Customer Care. My name is Priya. How may I assist you with your internet broadband plan today? Please do not share your confidential passwords or banking pins with anyone. I can help you upgrade your monthly speed package directly on your registered account.",
  },
];

export function AnalyzePage({ onNavigate }) {
  // Input Selection: 'upload' | 'text' | 'file_text'
  const [inputTab, setInputTab] = useState("upload");

  // Intake State
  const [file, setFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioDuration, setAudioDuration] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [speakerId, setSpeakerId] = useState("");

  // Processing & Execution State
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0); // 0 to 6
  const [processingMessage, setProcessingMessage] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Audio Playback
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Stale Request Invalidation & Abort Control
  const activeRequestIdRef = useRef(0);
  const abortControllerRef = useRef(null);

  // Sync audio URL when file changes
  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setAudioUrl(null);
      setAudioDuration(null);
      setIsPlaying(false);
    }
  }, [file]);

  const handleAudioLoadedMetadata = () => {
    if (audioRef.current) {
      setAudioDuration(audioRef.current.duration);
    }
  };

  const togglePlayAudio = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  // Reset entire workspace back to initial pristine state
  const handleReset = () => {
    activeRequestIdRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setFile(null);
    setAudioUrl(null);
    setAudioDuration(null);
    setTranscript("");
    setSpeakerId("");
    setIsProcessing(false);
    setProcessingStage(0);
    setProcessingMessage("");
    setAnalysis(null);
    setErrorMessage(null);
    setIsPlaying(false);
  };

  // Remove current audio recording and clear results immediately
  const handleRemoveFile = () => {
    activeRequestIdRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setFile(null);
    setAudioUrl(null);
    setAudioDuration(null);
    setTranscript("");
    setAnalysis(null);
    setErrorMessage(null);
    setIsProcessing(false);
    setProcessingStage(0);
    setProcessingMessage("");
    setIsPlaying(false);
  };

  // Validate Audio File Format & Size with immediate state wipe
  const validateAndSetAudioFile = (selectedFile) => {
    if (!selectedFile) return;

    // 1. Cancel any active requests immediately
    activeRequestIdRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // 2. Clear ALL old transcript and analysis results immediately
    setTranscript("");
    setAnalysis(null);
    setErrorMessage(null);
    setIsProcessing(false);
    setProcessingStage(0);
    setProcessingMessage("");
    setIsPlaying(false);

    const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
    if (selectedFile.size > MAX_SIZE) {
      setErrorMessage("File size exceeds the 50 MB limit. Please select a smaller recording.");
      setFile(null);
      return;
    }
    const validExtensions = [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aac", ".aiff"];
    const fileName = selectedFile.name.toLowerCase();
    const hasValidExt = validExtensions.some((ext) => fileName.endsWith(ext));
    const isAudioMime = selectedFile.type.startsWith("audio/") || selectedFile.type === "video/webm" || selectedFile.type === "video/ogg";

    if (!hasValidExt && !isAudioMime) {
      setErrorMessage("Unsupported audio format. Supported formats: WAV, MP3, M4A, FLAC, OGG, WEBM.");
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  // File Drop Handlers
  const handleFileDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      validateAndSetAudioFile(droppedFile);
    }
  };

  const handleTranscriptFileDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      readTranscriptFile(droppedFile);
    }
  };

  const readTranscriptFile = (textFile) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target.result;
      setTranscript(content);
      setInputTab("text");
      setErrorMessage(null);
    };
    reader.onerror = () => {
      setErrorMessage("Failed to read transcript text file.");
    };
    reader.readAsText(textFile);
  };

  // Automated Server-side Speech-to-Text
  const handleExtractStt = async () => {
    if (!file) {
      setErrorMessage("Please attach an audio recording first.");
      return;
    }

    activeRequestIdRef.current += 1;
    const currentReqId = activeRequestIdRef.current;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      setIsProcessing(true);
      setProcessingMessage("Transcribing audio through Speech-to-Text engine...");
      console.log("[AnalyzePage] Calling STT transcribe for file:", file.name, "Size:", file.size);
      const result = await transcribeAudio(file, { signal: controller.signal });

      if (currentReqId !== activeRequestIdRef.current) {
        console.log("[AnalyzePage] Stale STT response ignored for request ID:", currentReqId);
        return;
      }

      console.log("[AnalyzePage] STT response:", result);
      if (result.transcript && result.transcript.trim()) {
        setTranscript(result.transcript);
        setErrorMessage(null);
      } else if (result.warning) {
        setErrorMessage(`Transcription notice: ${result.warning} You can type or paste the transcript manually.`);
      } else {
        setErrorMessage("No audible speech could be transcribed from the file. You can enter the transcript manually.");
      }
      setIsProcessing(false);
      setProcessingMessage("");
    } catch (err) {
      if (currentReqId !== activeRequestIdRef.current || err.name === "CanceledError" || err.name === "AbortError") {
        return;
      }
      console.error("[AnalyzePage] STT extraction error:", err);
      setIsProcessing(false);
      setProcessingMessage("");
      if (err.code === "ECONNABORTED" || err.message?.toLowerCase().includes("timeout")) {
        setErrorMessage("Speech-to-Text transcription timed out. You can enter or paste the conversation transcript manually.");
      } else if (err.response) {
        const detail = err.response.data?.detail || err.response.data?.message || `Server error (${err.response.status})`;
        setErrorMessage(`Automatic transcription notice: ${detail}. You can enter or paste the transcript manually.`);
      } else if (err.request) {
        setErrorMessage("Unable to connect to the backend transcription service. You can enter or paste the transcript manually.");
      } else {
        setErrorMessage(`Automatic transcription unavailable (${err.message}). You can type or paste the transcript manually.`);
      }
    }
  };

  // Execute Forensic Analysis
  const handleRunAnalysis = async () => {
    setErrorMessage(null);
    const normalizedText = normalizeTranscript(transcript).trim();

    if (inputTab === "upload" && !file && !normalizedText) {
      setErrorMessage("Please select an audio recording or enter a transcript to analyze.");
      return;
    }
    if (inputTab === "text" && !normalizedText) {
      setErrorMessage("Please enter or paste conversation transcript text to evaluate.");
      return;
    }

    activeRequestIdRef.current += 1;
    const currentReqId = activeRequestIdRef.current;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsProcessing(true);
    setProcessingStage(1);
    setProcessingMessage("1/7 Uploading audio...");

    try {
      if (file) {
        console.log("[AnalyzePage] Running multimodal forensic analysis on file:", file.name, "with transcript length:", normalizedText.length);
        // Stage 1: Uploading audio
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;
        setProcessingStage(2);
        setProcessingMessage("2/7 Preparing audio & acoustic features...");

        // Stage 2: Preparing audio
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;
        setProcessingStage(3);
        setProcessingMessage("3/7 Transcribing speech (Server-side STT)...");

        // Stage 3: Transcribing speech
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;
        setProcessingStage(4);
        setProcessingMessage("4/7 Analyzing conversation & social engineering intent...");

        // Stage 4: Scam Intelligence & Risk Fusion
        const result = await analyzeAudio({
          file: file,
          transcript: normalizedText || undefined,
          speakerId: speakerId.trim() || undefined,
          signal: controller.signal,
        });

        if (currentReqId !== activeRequestIdRef.current) {
          console.log("[AnalyzePage] Stale analysis response dropped for request ID:", currentReqId);
          return;
        }

        console.log("[AnalyzePage] Multimodal analysis API response:", result);

        setProcessingStage(5);
        setProcessingMessage("5/7 Detecting voice authenticity & anti-spoofing...");
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;

        setProcessingStage(6);
        setProcessingMessage("6/7 Calculating multi-signal risk score...");
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;

        setProcessingStage(7);
        setProcessingMessage("7/7 Finalizing forensic assessment report...");
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;

        setAnalysis(result);
        if (result.transcript && (!transcript || transcript.trim() === "")) {
          setTranscript(result.transcript);
        }
        saveAnalysisRecord(result);
      } else {
        // Context Text Only Analysis
        console.log("[AnalyzePage] Running text-based NLP scam classification on transcript length:", normalizedText.length);
        setProcessingStage(2);
        setProcessingMessage("2/7 Preparing conversational linguistic tokens...");
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;

        setProcessingStage(4);
        setProcessingMessage("4/7 Analyzing conversation & intent classification...");

        const result = await analyzeContext(normalizedText, { signal: controller.signal });
        if (currentReqId !== activeRequestIdRef.current) return;

        console.log("[AnalyzePage] Text context analysis API response:", result);

        setProcessingStage(6);
        setProcessingMessage("6/7 Calculating conversational threat risk score...");
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;

        setProcessingStage(7);
        setProcessingMessage("7/7 Finalizing forensic assessment report...");
        await new Promise((r) => setTimeout(r, 60));
        if (currentReqId !== activeRequestIdRef.current) return;

        const finalScore = result.final_risk_score ?? result.context_risk_score ?? 0;
        const indicators = result.detected_indicators || [];
        const evidenceList = result.evidence || [];
        const finalCategory = result.final_scam_category || result.possible_scam_category || "Routine / Normal Call";
        const finalLevel = result.final_threat_level || result.risk_level || "LOW";

        const reportObj = {
          analysis_id: "forensic_" + Date.now().toString(36),
          created_at: new Date().toISOString(),
          analysis_status: "completed",
          final_risk_score: finalScore,
          risk_level: finalLevel,
          possible_scam_category: finalCategory,
          scam_category_confidence: result.scam_category_confidence || "HIGH",
          scam_category_description: result.scam_category_description || "Conversational intent evaluated against known telecommunication fraud patterns.",
          recommendation: result.recommendation || "Verify caller identity independently before sharing sensitive information.",
          detected_threats: indicators,
          scam_indicators: indicators,
          evidence: evidenceList,
          transcript: normalizedText,
          voice_authenticity: "NOT_EVALUATED",
          deepfake_probability: null,
          risk_reasoning: indicators.length > 0
            ? `Forensic analysis identified ${indicators.length} threat indicators in the submitted conversation content.`
            : "No high-confidence telecommunication fraud or coercion indicators were detected in the conversation content.",
        };

        setAnalysis(reportObj);
        saveAnalysisRecord(reportObj);
      }
    } catch (err) {
      if (currentReqId !== activeRequestIdRef.current || err.name === "CanceledError" || err.name === "AbortError") {
        return;
      }
      console.error("[AnalyzePage] Forensic analysis request error:", err);
      if (err.code === "ECONNABORTED" || err.message?.toLowerCase().includes("timeout")) {
        setErrorMessage("Audio analysis request timed out. The audio file may be large or complex. Please try again or provide the conversation transcript text directly.");
      } else if (err.response) {
        const errorDetail =
          err.response.data?.detail ||
          err.response.data?.message ||
          `Server returned error ${err.response.status}`;
        setErrorMessage(`Analysis failed: ${errorDetail}`);
      } else if (err.request) {
        setErrorMessage("Unable to connect to the backend server. Please verify the backend is running on port 8000.");
      } else {
        setErrorMessage(`Analysis request failed: ${err.message || "An unexpected error occurred."}`);
      }
    } finally {
      if (currentReqId === activeRequestIdRef.current) {
        setIsProcessing(false);
        setProcessingStage(0);
        setProcessingMessage("");
      }
    }
  };

  // Download Markdown Report
  const handleExportReport = () => {
    if (!analysis) return;
    const score = analysis.final_risk_score ?? "--";
    const level = analysis.risk_level ?? "UNKNOWN";
    const category = analysis.possible_scam_category ?? "Unknown";
    const recommendation = analysis.recommendation ?? "No recommendation available.";
    const voiceAuth = analysis.voice_authenticity ?? "Not Evaluated";
    const transcriptText = analysis.transcript ?? transcript ?? "None provided.";
    const indicators = analysis.detected_threats || analysis.scam_indicators || [];

    const mdContent = `# Voice Shield — Forensic Call Security Report
**Date:** ${new Date().toISOString()}
**Analysis ID:** ${analysis.analysis_id || "N/A"}

---

## 1. Executive Summary
- **Overall Threat Score:** ${score} / 100
- **Threat Level:** ${level} RISK
- **Scam Category:** ${category} (Confidence: ${analysis.scam_category_confidence || "N/A"})
- **Voice Authenticity:** ${voiceAuth}

### Recommended Immediate Action:
> ${recommendation}

---

## 2. Spoken Conversation Evidence & Transcript
\`\`\`text
${transcriptText}
\`\`\`

---

## 3. Detected Threat Indicators (${indicators.length})
${
  indicators.length > 0
    ? indicators
        .map(
          (ind, idx) =>
            `${idx + 1}. **${ind.label || ind.category}** [Severity: ${ind.severity || "HIGH"}]\n   - Matched Evidence: "${ind.matched_cue || "N/A"}"\n   - Rationale: ${ind.explanation || ind.why_it_matters || "Identified fraud cue."}`
        )
        .join("\n\n")
    : "No threat indicators detected."
}

---

## 4. Multi-Signal Security Principles
- **Human Voice ≠ Safe Call:** Scammers frequently use authentic human voices in digital arrest and banking extortion.
- **Voice Authenticity:** Acoustic anti-spoofing operates independently from conversational scam intent.

---
*Report generated by Voice Shield Forensic Call Investigation Workspace.*
`;

    const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `voice-shield-report-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatSeconds = (sec) => {
    if (!sec || isNaN(sec)) return "00:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="analyze-workspace-layout">
      {/* 1. Page Header */}
      <section className="page-intro-header flex justify-between items-start flex-wrap gap-4">
        <div>
          <span className="page-pretitle">POST-CALL FORENSIC INVESTIGATION</span>
          <h1 className="page-headline">Analyze a Call Recording</h1>
          <p className="page-subheadline">
            Examine a recorded audio file or conversation transcript to determine what happened during the call, identify social engineering tactics, and verify voice authenticity.
          </p>
        </div>

        <button
          type="button"
          className="secondary-btn flex items-center gap-1.5 self-center"
          onClick={handleReset}
          title="Clear all inputs and reset workspace"
        >
          <RotateCcw size={14} />
          <span>New Analysis</span>
        </button>
      </section>

      {/* 2. Main Workspace Layout */}
      <div className="product-workspace">
        {/* LEFT COLUMN: 3 DISTINCT POST-CALL INTAKE METHODS */}
        <section className="intake-column">
          <div className="intake-card">
            <div className="section-title-row">
              <h2 className="section-title">Call Intake &amp; File Ingestion</h2>
              <span className="section-meta">
                Status: <strong className="text-blue-700 font-semibold">{isProcessing ? "PROCESSING..." : analysis ? "ANALYSIS COMPLETE" : "READY"}</strong>
              </span>
            </div>

            {/* Input Method Switcher */}
            <div className="mode-toggle-bar">
              <button
                type="button"
                className={`mode-btn ${inputTab === "upload" ? "active-mode" : ""}`}
                onClick={() => { setInputTab("upload"); setErrorMessage(null); }}
              >
                <Upload size={14} />
                <span>Upload Audio File</span>
              </button>
              <button
                type="button"
                className={`mode-btn ${inputTab === "text" ? "active-mode" : ""}`}
                onClick={() => { setInputTab("text"); setErrorMessage(null); }}
              >
                <FileText size={14} />
                <span>Paste Transcript</span>
              </button>
              <button
                type="button"
                className={`mode-btn ${inputTab === "file_text" ? "active-mode" : ""}`}
                onClick={() => { setInputTab("file_text"); setErrorMessage(null); }}
              >
                <FileCheck size={14} />
                <span>Upload Text/Data</span>
              </button>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="status-banner banner-error mb-3">
                <AlertOctagon size={15} className="flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* TAB 1: AUDIO RECORDING UPLOAD */}
            {inputTab === "upload" && (
              <div className="upload-intake-box">
                {file ? (
                  <div className="selected-file-card mb-3">
                    <div className="file-icon-box">
                      <FileAudio size={22} className="text-blue-700" />
                    </div>
                    <div className="file-info-col">
                      <span className="file-name font-semibold text-slate-900">{file.name}</span>
                      <span className="file-meta text-xs text-slate-500">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB • {file.type || "Audio Recording"}
                        {audioDuration ? ` • Duration: ${formatSeconds(audioDuration)}` : ""}
                      </span>
                    </div>
                    <button
                      className="remove-file-btn text-slate-400 hover:text-red-600"
                      onClick={handleRemoveFile}
                      title="Remove file"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ) : (
                  <label
                    className="intake-dropzone"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleFileDrop}
                  >
                    <Upload size={24} className="intake-upload-icon text-blue-600 mb-2" />
                    <span className="dropzone-text font-semibold text-slate-800">
                      Drag &amp; drop call recording here or click to browse
                    </span>
                    <span className="dropzone-formats text-xs text-slate-500 mt-1">
                      Supported formats: WAV, MP3, M4A, FLAC, OGG, WEBM (Max 50 MB)
                    </span>
                    <input
                      type="file"
                      accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg,.webm"
                      onChange={(e) => {
                        if (e.target.files?.[0]) validateAndSetAudioFile(e.target.files[0]);
                      }}
                      className="hidden-file-input"
                    />
                  </label>
                )}

                {/* Built-in Audio Player Preview */}
                {audioUrl && (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700"
                          onClick={togglePlayAudio}
                        >
                          {isPlaying ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
                        </button>
                        <span className="text-xs font-semibold text-slate-700">Audio Preview Player</span>
                      </div>
                      <span className="text-xs font-mono text-slate-500">
                        {formatSeconds(audioDuration)}
                      </span>
                    </div>
                    <audio
                      ref={audioRef}
                      src={audioUrl}
                      onLoadedMetadata={handleAudioLoadedMetadata}
                      onEnded={() => setIsPlaying(false)}
                      controls
                      className="w-full h-8"
                    />
                  </div>
                )}

                {/* Optional Transcript / STT Extractor */}
                <div className="field-group mt-3">
                  <div className="flex justify-between items-center mb-1">
                    <label className="field-label text-xs font-semibold text-slate-700">
                      Call Transcript (Optional for Audio File)
                    </label>
                    <button
                      type="button"
                      className="subtle-link-btn flex items-center gap-1 text-xs text-blue-700"
                      onClick={handleExtractStt}
                      disabled={isProcessing || !file}
                    >
                      <RefreshCw size={12} className={isProcessing ? "spin-icon" : ""} />
                      <span>Extract with Speech-to-Text</span>
                    </button>
                  </div>
                  <textarea
                    className="clean-textarea text-xs"
                    rows={3}
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    placeholder="Enter transcript or leave blank for automatic server-side transcription..."
                  />
                </div>

                {/* Optional Speaker Biometric Reference */}
                <div className="field-group mt-3">
                  <label className="field-label text-xs font-semibold text-slate-700">
                    Known Speaker Reference ID (Optional)
                  </label>
                  <input
                    type="text"
                    className="clean-input text-xs"
                    value={speakerId}
                    onChange={(e) => setSpeakerId(e.target.value)}
                    placeholder="e.g. executive_cfo_01 (for speaker verification)"
                  />
                </div>
              </div>
            )}

            {/* TAB 2: PASTE CONVERSATION TRANSCRIPT */}
            {inputTab === "text" && (
              <div className="text-intake-box">
                <div className="field-group">
                  <div className="flex justify-between items-center mb-1">
                    <label className="field-label text-xs font-semibold text-slate-700">
                      Paste Conversation Transcript
                    </label>
                    <span className="text-2xs text-slate-400 font-mono">
                      {transcript.split(/\s+/).filter(Boolean).length} words
                    </span>
                  </div>
                  <textarea
                    className="clean-textarea text-xs"
                    rows={7}
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                    placeholder="Paste the full dialogue or suspicious call transcript here to analyze conversational intent, coercion tactics, and authority claims..."
                  />
                </div>

                {/* Quick Sample Loaders */}
                <div className="mt-3 pt-3 border-t border-slate-200">
                  <span className="text-2xs font-semibold uppercase tracking-wider text-slate-500 block mb-1.5">
                    Quick Test Samples:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {DEMO_SAMPLES.map((sample) => (
                      <button
                        key={sample.id}
                        type="button"
                        className="p-1.5 px-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs rounded border border-slate-200 text-left transition-colors"
                        onClick={() => {
                          setTranscript(sample.text);
                          setErrorMessage(null);
                        }}
                      >
                        <strong className="block text-2xs text-slate-900">{sample.label}</strong>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: UPLOAD TRANSCRIPT / CALL DATA FILE */}
            {inputTab === "file_text" && (
              <div className="file-text-intake-box">
                <label
                  className="intake-dropzone"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleTranscriptFileDrop}
                >
                  <FileText size={24} className="intake-upload-icon text-blue-600 mb-2" />
                  <span className="dropzone-text font-semibold text-slate-800">
                    Upload transcript document (.txt, .json, .vtt, .srt)
                  </span>
                  <span className="dropzone-formats text-xs text-slate-500 mt-1">
                    Text will be automatically extracted and loaded into the forensic analyzer
                  </span>
                  <input
                    type="file"
                    accept=".txt,.json,.vtt,.srt"
                    onChange={(e) => {
                      if (e.target.files?.[0]) readTranscriptFile(e.target.files[0]);
                    }}
                    className="hidden-file-input"
                  />
                </label>
              </div>
            )}

            {/* Primary Action Button */}
            <div className="action-buttons-row mt-4">
              <button
                type="button"
                className="primary-execute-btn"
                onClick={handleRunAnalysis}
                disabled={isProcessing || (inputTab === "upload" && !file && !transcript.trim()) || (inputTab === "text" && !transcript.trim())}
              >
                {isProcessing ? (
                  <>
                    <Loader2 size={16} className="spin-icon text-white" />
                    <span>Analyzing Call Recording...</span>
                  </>
                ) : (
                  <>
                    <Activity size={16} className="text-white" />
                    <span>{inputTab === "upload" && file ? "Analyze Audio Recording" : "Analyze Call Transcript"}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: FORENSIC ASSESSMENT REPORT & PIPELINE */}
        <section className="results-column">
          {/* PROCESSING STATE: 6-STAGE POST-CALL CANONICAL PIPELINE */}
          {isProcessing ? (
            <div className="security-report-card">
              <div className="report-summary-header">
                <span className="report-pretitle">EXECUTION PIPELINE</span>
                <h3 className="text-base font-bold text-slate-900 mt-1">
                  Processing Call Recording...
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">{processingMessage}</p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg my-4 space-y-2.5">
                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 1 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 1 ? <CheckCircle2 size={14} /> : "1"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">1. Uploading audio</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 2 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 2 ? <CheckCircle2 size={14} /> : "2"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">2. Preparing audio &amp; acoustic features</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 3 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 3 ? <CheckCircle2 size={14} /> : "3"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">3. Transcribing speech (Server-side Speech-to-Text)</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 4 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 4 ? <CheckCircle2 size={14} /> : "4"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">4. Analyzing conversation &amp; social engineering intent</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 5 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 5 ? <CheckCircle2 size={14} /> : "5"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">5. Detecting voice authenticity &amp; anti-spoofing</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 6 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 6 ? <CheckCircle2 size={14} /> : "6"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">6. Calculating multi-signal risk score</span>
                </div>

                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${processingStage >= 7 ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {processingStage > 7 ? <CheckCircle2 size={14} /> : "7"}
                  </div>
                  <span className="text-xs font-semibold text-slate-800">7. Finalizing forensic assessment report</span>
                </div>
              </div>
            </div>
          ) : !analysis ? (
            /* INITIAL EMPTY READY STATE */
            <div className="security-report-card">
              <div className="report-summary-header">
                <span className="report-pretitle">CALL SECURITY ASSESSMENT</span>
                <div className="flex justify-between items-start flex-wrap gap-3 mt-1 mb-3">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">Overall Threat</span>
                    <span className="risk-text-tag text-slate-500 text-lg mt-0.5">
                      NOT ANALYZED
                    </span>
                  </div>
                  <div className="report-score-pill">
                    <span className="score-num text-slate-400">—</span>
                    <span className="score-denom">/ 100</span>
                  </div>
                </div>
              </div>

              <div className="empty-workspace-state">
                <div className="empty-state-icon-wrap">
                  <Shield size={28} className="text-blue-700" />
                </div>
                <h3 className="empty-state-title">Ready for Post-Call Forensic Analysis</h3>
                <p className="empty-state-desc">
                  Select an existing audio recording or paste a transcript on the left to evaluate voice authenticity, extract spoken evidence, and classify telecommunication fraud tactics.
                </p>
                <div className="status-pill-subtle pill-neutral mt-4">
                  Forensic Workspace Standby • Awaiting input
                </div>
              </div>
            </div>
          ) : (
            /* COMPLETED FORENSIC REPORT */
            <div className="security-report-card">
              {/* 1. Report Header with Score & Export */}
              <div className="report-summary-header">
                <div className="flex justify-between items-center flex-wrap gap-2 mb-2">
                  <span className="report-pretitle">FORENSIC SECURITY REPORT</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="secondary-btn text-xs flex items-center gap-1.5 py-1 px-2.5"
                      onClick={handleExportReport}
                    >
                      <Download size={13} />
                      <span>Export Report (.md)</span>
                    </button>
                    <button
                      type="button"
                      className="subtle-link-btn"
                      onClick={handleReset}
                      title="Reset"
                    >
                      <RotateCcw size={12} />
                      <span>New</span>
                    </button>
                  </div>
                </div>

                <div className="flex justify-between items-start flex-wrap gap-3 mt-1 mb-3">
                  <div>
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">Overall Threat Level</span>
                    <span className={`risk-text-tag level-${(analysis.risk_level || "low").toLowerCase()} text-lg mt-0.5`}>
                      {analysis.risk_level || "LOW"} RISK
                    </span>
                  </div>
                  <div className="report-score-pill">
                    <span className={`score-num ${analysis.final_risk_score >= 75 ? "text-red-700" : analysis.final_risk_score >= 50 ? "text-red-600" : analysis.final_risk_score >= 25 ? "text-amber-700" : "text-emerald-700"}`}>
                      {analysis.final_risk_score ?? "--"}
                    </span>
                    <span className="score-denom">/ 100</span>
                  </div>
                </div>

                {/* Possible Scam Category Box */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-md mb-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">Possible Scam Category</span>
                      <strong className="text-base text-slate-900 mt-0.5 block">
                        {analysis.possible_scam_category || "Routine / Normal Call"}
                      </strong>
                    </div>
                    {analysis.scam_category_confidence && (
                      <span className={`status-pill-subtle ${analysis.scam_category_confidence === "HIGH" ? "pill-danger" : analysis.scam_category_confidence === "MEDIUM" ? "pill-warning" : "pill-neutral"}`}>
                        Confidence: {analysis.scam_category_confidence}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 mt-1.5">
                    {analysis.scam_category_description || "The conversation was evaluated against known telecommunications fraud patterns."}
                  </p>
                </div>

                {/* Recommended Action Box */}
                <div className="report-action-box">
                  <strong className="text-xs text-slate-900 block mb-0.5">Recommended Action:</strong>
                  <span className="text-xs text-blue-900 leading-relaxed block">{analysis.recommendation}</span>
                </div>
              </div>

              {/* 2. Spoken Conversation Evidence */}
              <div className="report-signals-section">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="report-section-heading">Spoken Conversation Transcript</h4>
                  <span className={`status-pill-subtle ${analysis.transcript ? "pill-safe" : "pill-warning"}`}>
                    {analysis.transcript ? "Transcribed" : "Content Unavailable"}
                  </span>
                </div>
                {analysis.transcript ? (
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-800 leading-relaxed">
                    <div className="flex items-start gap-2">
                      <Quote size={14} className="text-slate-400 flex-shrink-0 mt-0.5" />
                      <p className="italic font-medium">&quot;{analysis.transcript}&quot;</p>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-900 leading-relaxed">
                    <strong>Conversation Content Unavailable: </strong>
                    <span>No spoken dialogue was captured in this recording.</span>
                  </div>
                )}
              </div>

              {/* 3. Detected Threat Indicators Grid */}
              <div className="report-signals-section">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="report-section-heading">
                    Detected Threat Indicators ({(analysis.detected_threats || analysis.scam_indicators || []).length})
                  </h4>
                </div>
                {(analysis.detected_threats || analysis.scam_indicators || []).length > 0 ? (
                  <div className="space-y-2">
                    {(analysis.detected_threats || analysis.scam_indicators || []).map((ind, i) => (
                      <ThreatSignalCard key={i} signal={ind} index={i} />
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-900">
                    <CheckCircle2 size={14} className="inline mr-1 text-emerald-700" />
                    <span>No conversational scam indicators or social engineering pressure tactics detected.</span>
                  </div>
                )}
              </div>

              {/* 4. Voice Authenticity Analysis */}
              <div className="report-signals-section">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="report-section-heading">Voice Authenticity &amp; Anti-Spoofing</h4>
                  <span className={`status-pill-subtle ${analysis.voice_authenticity === "HIGH_CONFIDENCE_SYNTHETIC" ? "pill-danger" : analysis.voice_authenticity === "POSSIBLE_SYNTHETIC" ? "pill-warning" : analysis.voice_authenticity === "NOT_EVALUATED" ? "pill-neutral" : "pill-safe"}`}>
                    {analysis.voice_authenticity === "NOT_EVALUATED" ? "Not Evaluated (Text Only)" : analysis.voice_authenticity === "HIGH_CONFIDENCE_SYNTHETIC" ? "Strong Synthetic Detection" : analysis.voice_authenticity === "POSSIBLE_SYNTHETIC" ? "Suspicious Characteristics" : analysis.voice_authenticity === "INSUFFICIENT_AUDIO" ? "Insufficient Audio" : "Likely Human"}
                  </span>
                </div>
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-700 leading-relaxed">
                  <p>
                    {analysis.voice_authenticity === "NOT_EVALUATED"
                      ? "Voice Authenticity: Not Evaluated. Reason: Analysis was performed on a text transcript without an audio recording."
                      : analysis.voice_authenticity === "HIGH_CONFIDENCE_SYNTHETIC"
                      ? `Neural anti-spoofing model verified synthetic vocoder artifacts (${Math.round((analysis.deepfake_probability || 0) * 100)}% confidence).`
                      : analysis.voice_authenticity === "INSUFFICIENT_AUDIO"
                      ? "The available audio was insufficient to perform a reliable synthetic voice determination."
                      : "Acoustic spectrogram dynamics match natural biological human speech parameters."}
                  </p>
                  <div className="flex items-center gap-3 mt-2 pt-2 border-t border-slate-200 text-slate-500 font-medium text-2xs">
                    <span className="text-emerald-700 font-semibold">Human Voice ≠ Safe Call</span>
                    <span>•</span>
                    <span className="text-slate-700">Synthetic Voice ≠ Automatically a Scam</span>
                  </div>
                </div>
              </div>

              {/* 5. Why This Call Was Flagged */}
              <div className="report-signals-section">
                <h4 className="report-section-heading">Why This Call Was Flagged</h4>
                <div className="p-3 bg-blue-50/50 border border-blue-200/80 rounded-md text-xs text-slate-700 leading-relaxed">
                  <p>
                    {analysis.risk_reasoning || "Multi-signal evaluation completed across acoustic voice authenticity and conversational threat intent."}
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
