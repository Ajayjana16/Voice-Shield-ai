import React, { useState } from "react";
import {
  Activity,
  Sliders,
  FileText,
  Shield,
  Layers,
  ArrowRight,
  CheckCircle2,
  Lock,
  ShieldAlert,
  Cpu,
  ChevronDown,
  ChevronUp,
  Zap,
  KeyRound,
  Scale,
  Sparkles,
  Radio,
  Binary,
  Workflow,
  ShieldCheck,
  Code2,
  Waves,
  AudioWaveform,
} from "lucide-react";

export function HowItWorksPage({ onNavigate }) {
  const [isTechOpen, setIsTechOpen] = useState(true);

  return (
    <div className="how-it-works-layout">
      {/* 1. Page Header with subtle cybersecurity badge */}
      <section className="page-intro-header">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-2 border border-blue-200">
          <Workflow size={13} />
          <span>MULTI-SIGNAL DETECTION PIPELINE</span>
        </div>
        <h1 className="page-headline">How Voice Shield Works</h1>
        <p className="page-subheadline">
          An explainable, dual-engine voice security architecture combining neural acoustic anti-spoofing, real-time linguistic intent analysis, and deterministic risk fusion.
        </p>
      </section>

      {/* 2. Canonical 6-Stage Core Pipeline */}
      <section className="how-card-section">
        <div className="how-section-header">
          <span className="section-step-tag">Step-by-Step Processing</span>
          <h2 className="how-section-title">The 6-Stage Analysis Pipeline</h2>
          <p className="how-section-desc">
            Every audio interaction passes through six transparent evaluation stages to ensure accurate, explainable scam detection.
          </p>
        </div>

        <div className="arch-flow-diagram">
          <div className="arch-flow-step">
            <span className="flow-step-badge">Stage 01</span>
            <h4>Audio Ingestion</h4>
            <p>
              Continuous stream or uploaded file converted to uniform 16 kHz buffers with energy-based noise thresholding.
            </p>
          </div>

          <div className="arch-flow-step">
            <span className="flow-step-badge">Stage 02</span>
            <h4>Speech Detection / VAD</h4>
            <p>
              Voice Activity Detection separates active voiced speech from silence, avoiding false triggers on background noise.
            </p>
          </div>

          <div className="arch-flow-step">
            <span className="flow-step-badge">Stage 03</span>
            <h4>Voice Authenticity</h4>
            <p>
              Acoustic neural transformers evaluate vocoder spectrograms and phase continuity to detect AI-cloned or synthetic speech.
            </p>
          </div>

          <div className="arch-flow-step">
            <span className="flow-step-badge">Stage 04</span>
            <h4>Scam Intelligence</h4>
            <p>
              Linguistic algorithms classify conversational commands, digital arrest claims, OTP harvesting, and psychological urgency.
            </p>
          </div>

          <div className="arch-flow-step">
            <span className="flow-step-badge">Stage 05</span>
            <h4>Risk Fusion</h4>
            <p>
              Deterministic scoring fuses independent acoustic and conversational evidence with consistency floors for critical fraud cues.
            </p>
          </div>

          <div className="arch-flow-step">
            <span className="flow-step-badge">Stage 06</span>
            <h4>Threat Assessment</h4>
            <p>
              Outputs calibrated 0–100 threat scores, classified scam categories, confidence ratings, and actionable defense guidance.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Core Security Principle Banner */}
      <section className="principle-banner-card">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-amber-50 text-amber-700 rounded-lg flex-shrink-0 mt-0.5 border border-amber-200">
            <ShieldAlert size={20} />
          </div>
          <div>
            <span className="status-pill-subtle pill-warning mb-1.5 inline-block">Fundamental Principle</span>
            <h3 className="text-sm font-bold text-slate-900 mb-1">
              No single signal determines whether a call is fraudulent.
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              An authentic human voice does not make a call safe if the caller is demanding an urgent OTP or threatening arrest under a fake police warrant. Likewise, unusual acoustic background noise does not mean a call is malicious. Voice Shield evaluates voice authenticity and conversational threat intent as distinct, orthogonal dimensions.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Two Independent Analysis Dimensions */}
      <section className="how-card-section">
        <div className="how-section-header">
          <span className="section-step-tag">Orthogonal Dimensions</span>
          <h2 className="how-section-title">Acoustic Authenticity vs. Conversational Threat</h2>
          <p className="how-section-desc">
            Understanding why authentic human voices can still be flagged as critical security threats.
          </p>
        </div>

        <div className="contrast-grid">
          <div className="contrast-card">
            <div className="contrast-header">
              <div className="p-1.5 rounded bg-blue-50 text-blue-700">
                <Activity size={16} />
              </div>
              <h3>Voice Authenticity Analysis</h3>
            </div>
            <div className="contrast-question">
              <strong>Question:</strong> Is this voice artificially generated or cloned by AI?
            </div>
            <ul className="contrast-bullets">
              <li>Inspects vocoder spectrogram inversion and high-frequency phase artifacts.</li>
              <li>Detects dynamic range over-smoothing typical of generative speech models.</li>
              <li>Operates locally without requiring voice enrollment or biometric profiles.</li>
              <li>Identifies synthetic speech used in executive impersonation and clone attacks.</li>
            </ul>
          </div>

          <div className="contrast-card">
            <div className="contrast-header">
              <div className="p-1.5 rounded bg-red-50 text-red-700">
                <ShieldAlert size={16} />
              </div>
              <h3>Conversation &amp; Scam Intelligence</h3>
            </div>
            <div className="contrast-question">
              <strong>Question:</strong> Is the caller attempting extortion, fraud, or credential theft?
            </div>
            <ul className="contrast-bullets">
              <li>Detects digital arrest extortion, fake CBI/police, and court summons threats.</li>
              <li>Identifies urgent fund transfer demands and netbanking OTP requests.</li>
              <li>Flags courier contraband claims and fake tech support remote access requests.</li>
              <li>Enforces critical threat ratings even when the caller is an authentic human.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 5. Dark Navy Cybersecurity Technical Architecture Section (Clean One-Row Pipeline) */}
      <section className="tech-arch-cyber-card">
        {/* Visual Pipeline Flow Header */}
        <div className="tech-arch-cyber-header">
          <div className="flex items-center gap-3">
            <div className="tech-header-icon-box">
              <Cpu size={22} className="text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="tech-header-badge">CORE ARCHITECTURE</span>
                <span className="tech-header-dot" />
                <span className="tech-header-status">MULTI-SIGNAL PIPELINE</span>
              </div>
              <h2 className="tech-arch-title">TECHNICAL ARCHITECTURE</h2>
              <p className="tech-arch-subtitle">
                Model specifications, feature extraction methods, and multi-signal risk fusion.
              </p>
            </div>
          </div>
          
          <button
            type="button"
            className="tech-collapse-control"
            onClick={() => setIsTechOpen(!isTechOpen)}
            aria-expanded={isTechOpen}
          >
            <span>{isTechOpen ? "Collapse Architecture" : "Expand Architecture"}</span>
            {isTechOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        </div>

        {/* End-to-End Pipeline Ribbon: Fully Visible in One Row with Subtle Flow Indicators */}
        <div className="tech-pipeline-ribbon">
          <div className="pipeline-crumb">
            <span className="crumb-num">01</span>
            <span className="crumb-text">Audio Ingest</span>
          </div>
          
          <div className="pipeline-flow-connector">
            <span className="flow-dot" />
            <span className="flow-arrow">→</span>
          </div>

          <div className="pipeline-crumb">
            <span className="crumb-num">02</span>
            <span className="crumb-text">Speech VAD</span>
          </div>
          
          <div className="pipeline-flow-connector">
            <span className="flow-dot" />
            <span className="flow-arrow">→</span>
          </div>

          <div className="pipeline-crumb">
            <span className="crumb-num">03</span>
            <span className="crumb-text">Voice Authenticity</span>
          </div>
          
          <div className="pipeline-flow-connector">
            <span className="flow-dot" />
            <span className="flow-arrow">→</span>
          </div>

          <div className="pipeline-crumb">
            <span className="crumb-num">04</span>
            <span className="crumb-text">Scam Intelligence</span>
          </div>
          
          <div className="pipeline-flow-connector">
            <span className="flow-dot" />
            <span className="flow-arrow">→</span>
          </div>

          <div className="pipeline-crumb highlight">
            <span className="crumb-num">05</span>
            <span className="crumb-text">Risk Fusion</span>
          </div>
          
          <div className="pipeline-flow-connector">
            <span className="flow-dot" />
            <span className="flow-arrow">→</span>
          </div>

          <div className="pipeline-crumb success">
            <span className="crumb-num">06</span>
            <span className="crumb-text">Threat Assessment</span>
          </div>
        </div>

        {isTechOpen && (
          <div className="tech-arch-cyber-grid">
            {/* Acoustic Model Card */}
            <div className="tech-cyber-box box-acoustic">
              <div className="tech-box-header">
                <span className="tech-cyber-badge badge-cyan">
                  Acoustic Model
                </span>
                <span className="tech-box-sublabel">VoiceShield-Acoustic-v2</span>
              </div>
              <p className="tech-box-desc">
                Pretrained Wav2Vec2 transformer fine-tuned for deepfake detection, with fallback to handcrafted spectral flux, zero-crossing rate, and energy dynamics.
              </p>
              <div className="tech-spec-row">
                <span className="spec-tag">16 kHz Sample Rate</span>
                <span className="spec-tag">Phase Inversion Analysis</span>
              </div>
            </div>

            {/* Linguistic Engine Card */}
            <div className="tech-cyber-box box-linguistic">
              <div className="tech-box-header">
                <span className="tech-cyber-badge badge-purple">
                  Linguistic Engine
                </span>
                <span className="tech-box-sublabel">Intent State Machine</span>
              </div>
              <p className="tech-box-desc">
                Contextual pattern matcher evaluating 13 fraud categories across English and Indian multilingual contexts (Hindi, Hinglish, Tamil, Telugu) with defensive phrase filtering.
              </p>
              <div className="tech-spec-row">
                <span className="spec-tag">Multilingual N-Gram</span>
                <span className="spec-tag">Contextual Urgency VAD</span>
              </div>
            </div>

            {/* Risk Fusion Card */}
            <div className="tech-cyber-box box-fusion">
              <div className="tech-box-header">
                <span className="tech-cyber-badge badge-emerald">
                  Risk Fusion
                </span>
                <span className="tech-box-sublabel">Formula Weights</span>
              </div>
              
              {/* Highlighted Dedicated Formula Box */}
              <div className="tech-formula-highlight">
                <div className="formula-header">
                  <Code2 size={13} className="text-emerald-400" />
                  <span className="formula-label">FUSION CALCULATION</span>
                </div>
                <code className="formula-code">
                  Threat = 0.40×Deepfake + 0.45×Context + 0.15×Prosody
                </code>
              </div>

              {/* Compact 3-Input Weight Labels */}
              <div className="fusion-weights-row">
                <div className="weight-chip chip-deepfake">
                  <span className="weight-pct">40%</span>
                  <span className="weight-name">Deepfake Signal</span>
                </div>
                <div className="weight-chip chip-context">
                  <span className="weight-pct">45%</span>
                  <span className="weight-name">Context Engine</span>
                </div>
                <div className="weight-chip chip-prosody">
                  <span className="weight-pct">15%</span>
                  <span className="weight-name">Prosody Signal</span>
                </div>
              </div>

              <p className="tech-box-desc mt-2.5">
                Enforces deterministic consistency floors for critical severity cues (OTP, Digital Arrest, Wire Transfer).
              </p>
            </div>
          </div>
        )}
      </section>

      {/* 6. Compact Final CTA Card */}
      <section className="how-cta-banner">
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Ready to evaluate a suspicious recording?</h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Upload audio or test sample scam scenarios in the investigation workspace.
            </p>
          </div>
          <button className="primary-cta-btn" onClick={() => onNavigate("/analyze")}>
            <span>Open Analysis Workspace</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </section>
    </div>
  );
}
