import React from "react";
import { CheckCircle2, Loader2, ChevronRight, Clock, ShieldCheck, AlertCircle } from "lucide-react";

const PIPELINE_STAGES = [
  {
    id: "intake",
    num: 1,
    title: "Audio Ingest",
    desc: "Continuous 16 kHz stream capture",
  },
  {
    id: "vad",
    num: 2,
    title: "Speech Detection",
    desc: "Voice Activity Detection (VAD)",
  },
  {
    id: "deepfake",
    num: 3,
    title: "Voice Authenticity",
    desc: "Independent acoustic verification",
  },
  {
    id: "context",
    num: 4,
    title: "Scam Intelligence",
    desc: "Contextual conversational intent",
  },
  {
    id: "fusion",
    num: 5,
    title: "Threat Assessment",
    desc: "Calibrated risk scoring & advice",
  },
];

export function PipelineSteps({
  analysis,
  isLoading,
  isLive,
  speechActivity,
  hasTranscript,
  isAnalyzing,
  liveAnalysis,
}) {
  const getStageState = (stageId) => {
    // 1. Live Streaming Mode Fine-Grained Resolution
    if (isLive) {
      if (stageId === "intake") {
        return { status: "completed", badge: "Streaming" };
      }
      if (stageId === "vad") {
        if (speechActivity === "speaking") {
          return { status: "loading", badge: "Speech Active" };
        }
        if (hasTranscript) {
          return { status: "completed", badge: "Speech Detected" };
        }
        return { status: "pending", badge: "Waiting for Speech" };
      }
      if (stageId === "deepfake") {
        const authStatus = liveAnalysis?.voiceAuthenticity;
        if (authStatus && authStatus !== "Insufficient Audio" && authStatus !== "Analyzing Voice") {
          return { status: "completed", badge: "Evaluated" };
        }
        if (speechActivity === "speaking") {
          return { status: "loading", badge: "Analyzing Voice" };
        }
        return { status: "pending", badge: "Waiting for Audio" };
      }
      if (stageId === "context") {
        if (isAnalyzing) {
          return { status: "loading", badge: "Evaluating Intent" };
        }
        if (
          liveAnalysis?.scamCategory &&
          liveAnalysis.scamCategory !== "Listening for speech..." &&
          liveAnalysis.scamCategory !== "Analyzing conversation..."
        ) {
          return { status: "completed", badge: "Classified" };
        }
        if (hasTranscript) {
          return { status: "completed", badge: "Monitoring" };
        }
        return { status: "pending", badge: "Waiting for Words" };
      }
      if (stageId === "fusion") {
        if (isAnalyzing) {
          return { status: "loading", badge: "Recalculating" };
        }
        if (
          liveAnalysis?.riskScore != null ||
          (liveAnalysis?.threatLevel && liveAnalysis.threatLevel !== "EVALUATING")
        ) {
          return { status: "completed", badge: "Assessed" };
        }
        return { status: "pending", badge: "Waiting for Evidence" };
      }
    }

    // 2. Non-live Loading Mode
    if (isLoading) {
      return { status: "loading", badge: "Processing" };
    }

    // 3. Completed Static Analysis Mode
    if (analysis) {
      if (analysis.analysis_status === "insufficient_audio") {
        if (stageId === "intake" || stageId === "vad") {
          return { status: "completed", badge: "Evaluated" };
        }
        return { status: "skipped", badge: "Skipped (No speech)" };
      }
      if (analysis.analysis_status === "partial_analysis" && stageId === "context") {
        return { status: "skipped", badge: "No transcript" };
      }
      return { status: "completed", badge: "Complete" };
    }

    // 4. Idle Ready State
    return { status: "pending", badge: "Idle" };
  };

  return (
    <div className="analysis-pipeline-container" aria-label="Audio Analysis Workflow Pipeline">
      <div className="pipeline-header-strip">
        <span className="pipeline-strip-title">SECURITY ANALYSIS PIPELINE</span>
        <span className="pipeline-strip-status">
          {isLive
            ? isAnalyzing
              ? "Evaluating conversation intent in real time..."
              : speechActivity === "speaking"
              ? "Speech detected — transcribing and monitoring..."
              : "Continuous live surveillance active • Listening for speech..."
            : isLoading
            ? "Evaluating audio and scam signals..."
            : analysis
            ? "Evaluation complete"
            : "Ready for input"}
        </span>
      </div>

      <div className="pipeline-stages-track">
        {PIPELINE_STAGES.map((stage, idx) => {
          const { status, badge } = getStageState(stage.id);
          const isDone = status === "completed";
          const isProcessing = status === "loading";
          const isSkipped = status === "skipped";

          return (
            <React.Fragment key={stage.id}>
              <div
                className={`pipeline-stage-card ${
                  isDone
                    ? "stage-done"
                    : isProcessing
                    ? "stage-active"
                    : isSkipped
                    ? "stage-skipped"
                    : "stage-pending"
                }`}
              >
                <div className="stage-top-row">
                  <div className="stage-marker">
                    {isProcessing ? (
                      <Loader2 size={13} className="spin-icon text-blue-600" />
                    ) : isDone ? (
                      <CheckCircle2 size={14} className="text-emerald-600" />
                    ) : (
                      <span className="stage-num-text">{stage.num}</span>
                    )}
                  </div>
                  <span className="stage-state-pill">{badge}</span>
                </div>

                <div className="stage-content-body">
                  <h4 className="stage-main-title">{stage.title}</h4>
                  <p className="stage-sub-desc">{stage.desc}</p>
                </div>
              </div>

              {idx < PIPELINE_STAGES.length - 1 && (
                <div className="pipeline-connector-arrow" aria-hidden="true">
                  <ChevronRight size={16} className="connector-chevron" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
