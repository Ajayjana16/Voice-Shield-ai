import React from "react";
import {
  Shield,
  Activity,
  ArrowRight,
  CheckCircle2,
  Lock,
  Landmark,
  ShieldAlert,
  Radio,
  KeyRound,
  CreditCard,
  UserX,
  Headphones,
  AlertTriangle,
  Layers,
  ShieldCheck,
  Zap,
  Quote,
  Users,
  Fingerprint,
  Waves,
  AudioWaveform,
  Sliders,
  Sparkles,
} from "lucide-react";

export function LandingPage({ onNavigate }) {
  return (
    <div className="landing-layout">
      {/* 1. HERO SECTION WITH BALANCED 2-COLUMN LAYOUT */}
      <section className="hero-section">
        {/* Left Column: Headline, Description, CTAs & Technology Pills */}
        <div className="hero-content">
          <div className="hero-badge">
            <span className="hero-badge-dot" />
            <span>AI Voice Security &amp; Fraud Defense</span>
          </div>

          <h1 className="hero-headline">
            Real-Time Voice Scam &amp; AI Clone Detection
          </h1>

          <p className="hero-subheading">
            AI-powered scam detection, real-time call monitoring, voice authenticity analysis, and conversational threat intelligence — protecting individuals and organizations from telecommunication fraud.
          </p>

          <div className="hero-cta-row">
            <button className="primary-cta-btn btn-large" onClick={() => onNavigate("/analyze")}>
              <Activity size={16} />
              <span>Analyze a Call</span>
            </button>
            <button className="secondary-cta-btn btn-large" onClick={() => onNavigate("/live")}>
              <Radio size={16} className="text-blue-700" />
              <span>Start Live Monitoring</span>
            </button>
          </div>

          {/* Structured Technology Indicator Badges */}
          <div className="hero-telemetry-strip">
            <span className="telemetry-pill">
              <span className="telemetry-dot dot-cyan" />
              <span>16 kHz Continuous Stream</span>
            </span>
            <span className="telemetry-pill">
              <span className="telemetry-dot dot-blue" />
              <span>Wav2Vec2 Neural Audio Model</span>
            </span>
            <span className="telemetry-pill">
              <span className="telemetry-dot dot-emerald" />
              <span>Contextual Scam VAD</span>
            </span>
          </div>

          <div className="hero-highlights-strip">
            <div className="highlight-item">
              <CheckCircle2 size={16} className="highlight-icon text-emerald-700 flex-shrink-0" />
              <span className="highlight-text">Immediate analysis without voice registration or biometric enrollment</span>
            </div>
            <div className="highlight-item">
              <CheckCircle2 size={16} className="highlight-icon text-emerald-700 flex-shrink-0" />
              <span className="highlight-text">Detects digital arrest extortion, banking fraud, OTP theft, and authority claims</span>
            </div>
            <div className="highlight-item">
              <CheckCircle2 size={16} className="highlight-icon text-emerald-700 flex-shrink-0" />
              <span className="highlight-text">Independent signals: authentic human voices can still conduct dangerous scams</span>
            </div>
          </div>
        </div>

        {/* Right Column: Simulated Live Surveillance Feed Demonstration Card */}
        <div className="hero-visual-card">
          <div className="visual-card-header">
            <div className="card-lights">
              <span className="light light-red" />
              <span className="light light-amber" />
              <span className="light light-green" />
            </div>
            <div className="flex items-center gap-2">
              <span className="visual-card-title">SIMULATED SURVEILLANCE FEED</span>
              <span className="live-status-pill demo-badge-pill">
                <span className="demo-status-dot" />
                <span>DEMO PREVIEW</span>
              </span>
            </div>
            <span className="status-pill-subtle pill-danger font-mono font-bold">CRITICAL RISK</span>
          </div>

          <div className="visual-card-body">
            {/* Threat Score & Scam Category Header Box */}
            <div className="preview-eval-summary">
              <div className="flex justify-between items-start flex-wrap gap-2">
                <div>
                  <span className="text-2xs text-slate-500 font-semibold uppercase tracking-wider block">Possible Scam Category</span>
                  <div className="text-base font-bold text-slate-900 mt-0.5">
                    OTP &amp; Credential Theft Attempt
                  </div>
                </div>
                <div className="report-score-pill">
                  <span className="score-num text-red-700">85</span>
                  <span className="score-denom">/ 100</span>
                </div>
              </div>
              <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">
                The conversation actively solicits one-time passwords and uses urgent time pressure to bypass verification.
              </p>
            </div>

            {/* Independent Signal Results */}
            <div className="preview-stat-row">
              <div className="preview-stat-box">
                <span className="preview-stat-k">Voice Authenticity</span>
                <span className="preview-stat-v text-emerald-700">Likely Human</span>
                <span className="text-xs text-slate-500 mt-0.5 block">Natural vocal harmonics</span>
              </div>
              <div className="preview-stat-box">
                <span className="preview-stat-k">Conversation Threat</span>
                <span className="preview-stat-v text-red-700">Critical Risk</span>
                <span className="text-xs text-slate-500 mt-0.5 block">Active OTP theft demand</span>
              </div>
            </div>

            {/* Compact Threat Signal Breakdown */}
            <div className="preview-signals-breakdown">
              <div className="signals-header">
                <span className="signals-title">DETECTED THREAT SIGNALS</span>
                <span className="signals-counter">3 Detected</span>
              </div>
              <div className="space-y-1.5">
                <div className="threat-signal-card">
                  <div className="threat-signal-header">
                    <div className="threat-signal-title-group">
                      <span className="threat-signal-dot dot-critical" />
                      <strong className="threat-signal-name">Request for OTP / Verification Code</strong>
                    </div>
                    <span className="threat-signal-badge badge-critical">CRITICAL</span>
                  </div>
                  <p className="threat-signal-explanation">
                    The caller requested a one-time password or verification code.
                  </p>
                  <div className="threat-signal-evidence">
                    <span className="threat-signal-evidence-label">Detected phrase:</span>
                    <span className="threat-signal-evidence-text">&quot;tell the OTP that you received&quot;</span>
                  </div>
                </div>

                <div className="threat-signal-card">
                  <div className="threat-signal-header">
                    <div className="threat-signal-title-group">
                      <span className="threat-signal-dot dot-high" />
                      <strong className="threat-signal-name">Urgency &amp; Psychological Time Pressure</strong>
                    </div>
                    <span className="threat-signal-badge badge-high">HIGH</span>
                  </div>
                  <p className="threat-signal-explanation">
                    The caller used urgency or pressure tactics to force immediate action.
                  </p>
                  <div className="threat-signal-evidence">
                    <span className="threat-signal-evidence-label">Detected phrase:</span>
                    <span className="threat-signal-evidence-text">&quot;right now immediately&quot;</span>
                  </div>
                </div>

                <div className="threat-signal-card">
                  <div className="threat-signal-header">
                    <div className="threat-signal-title-group">
                      <span className="threat-signal-dot dot-high" />
                      <strong className="threat-signal-name">Government / Police Impersonation</strong>
                    </div>
                    <span className="threat-signal-badge badge-high">HIGH</span>
                  </div>
                  <p className="threat-signal-explanation">
                    The caller claimed official authority from bank security or police.
                  </p>
                  <div className="threat-signal-evidence">
                    <span className="threat-signal-evidence-label">Detected phrase:</span>
                    <span className="threat-signal-evidence-text">&quot;officer from bank security&quot;</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Live Spoken Transcript Stream Preview */}
            <div className="preview-transcript-box">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <Quote size={12} className="text-blue-700" />
                  <span>Sample Spoken Transcript</span>
                </span>
                <span className="text-xs font-mono text-slate-500 font-semibold flex items-center gap-1">
                  Simulation Stream
                </span>
              </div>
              <div className="space-y-1.5 text-xs text-slate-800 font-mono bg-white p-2.5 rounded border border-slate-200 shadow-2xs">
                <div className="flex items-start gap-2">
                  <span className="text-slate-400 font-bold mt-0.5">00:18</span>
                  <span className="text-slate-900">&quot;Please share the OTP sent to your mobile...&quot;</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-slate-400 font-bold mt-0.5">00:22</span>
                  <span className="text-red-700 font-bold">&quot;This is required immediately to verify your account.&quot;</span>
                </div>
              </div>
            </div>

            {/* Recommended Immediate Action */}
            <div className="report-action-box">
              <strong className="text-xs text-slate-900 block mb-0.5">Recommended Immediate Action:</strong>
              <span className="text-xs text-blue-900 leading-relaxed block font-medium">
                Do NOT disclose the OTP. Financial institutions never ask for codes over the phone. Disconnect immediately.
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. THREE CORE CAPABILITIES / FEATURE CARDS */}
      <section className="compact-feature-row">
        <div className="feature-highlight-card">
          <div className="feature-card-header-bar">
            <div className="feature-highlight-icon bg-blue-50 text-blue-700 border border-blue-200">
              <Zap size={20} />
            </div>
            <span className="feature-card-number">01</span>
          </div>
          <div className="feature-highlight-content">
            <h3 className="feature-highlight-title">Real-Time Detection</h3>
            <p className="feature-highlight-desc">
              Continuously analyzes incoming speech streams during live calls, flagging scam phrasing and coercion patterns within seconds.
            </p>
          </div>
        </div>

        <div className="feature-highlight-card">
          <div className="feature-card-header-bar">
            <div className="feature-highlight-icon bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Layers size={20} />
            </div>
            <span className="feature-card-number">02</span>
          </div>
          <div className="feature-highlight-content">
            <h3 className="feature-highlight-title">Multi-Signal Analysis</h3>
            <p className="feature-highlight-desc">
              Evaluates conversational intent and acoustic voice authenticity as independent signals with fully explainable threat scoring.
            </p>
          </div>
        </div>

        <div className="feature-highlight-card">
          <div className="feature-card-header-bar">
            <div className="feature-highlight-icon bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Lock size={20} />
            </div>
            <span className="feature-card-number">03</span>
          </div>
          <div className="feature-highlight-content">
            <h3 className="feature-highlight-title">Privacy Focused</h3>
            <p className="feature-highlight-desc">
              Engineered for local ephemeral session execution without requiring prior voice enrollment, reference storage, or biometric databases.
            </p>
          </div>
        </div>
      </section>

      {/* 3. WHAT VOICE SHIELD DETECTS (PROFESSIONAL THREAT CATEGORIES GRID) */}
      <section className="what-detects-section">
        <div className="section-head-center mb-5">
          <span className="section-pretitle">Threat Categories</span>
          <h2 className="section-main-title">What Voice Shield Detects</h2>
          <p className="section-main-desc">
            Voice Shield continuously inspects conversational intent and vocal acoustic markers against established and emerging fraud vectors.
          </p>
        </div>

        <div className="detects-grid">
          {/* 1. OTP & Credential Theft */}
          <div className="detect-card">
            <div className="detect-card-header">
              <div className="detect-icon-box text-red-600 bg-red-50 border border-red-200">
                <KeyRound size={20} />
              </div>
              <span className="detect-severity-badge badge-critical">Critical Vector</span>
            </div>
            <h3 className="detect-card-title">OTP &amp; Credential Theft</h3>
            <p className="detect-card-desc">
              Direct prompts for one-time passwords, 2FA codes, PINs, banking passwords, or verification SMS tokens.
            </p>
          </div>

          {/* 2. Digital Arrest Scams */}
          <div className="detect-card">
            <div className="detect-card-header">
              <div className="detect-icon-box text-purple-600 bg-purple-50 border border-purple-200">
                <ShieldAlert size={20} />
              </div>
              <span className="detect-severity-badge badge-critical">Critical Vector</span>
            </div>
            <h3 className="detect-card-title">Digital Arrest Scams</h3>
            <p className="detect-card-desc">
              Fabricated police, CBI, or judicial summons demanding immediate video isolation and asset transfer to avoid arrest.
            </p>
          </div>

          {/* 3. Banking Fraud */}
          <div className="detect-card">
            <div className="detect-card-header">
              <div className="detect-icon-box text-blue-600 bg-blue-50 border border-blue-200">
                <Landmark size={20} />
              </div>
              <span className="detect-severity-badge badge-high">High Risk</span>
            </div>
            <h3 className="detect-card-title">Banking Fraud</h3>
            <p className="detect-card-desc">
              Fake KYC expiration notices, account freeze alerts, unauthorized charge pretexts, and urgent wire transfer demands.
            </p>
          </div>

          {/* 4. Authority Impersonation */}
          <div className="detect-card">
            <div className="detect-card-header">
              <div className="detect-icon-box text-indigo-600 bg-indigo-50 border border-indigo-200">
                <Users size={20} />
              </div>
              <span className="detect-severity-badge badge-high">High Risk</span>
            </div>
            <h3 className="detect-card-title">Authority Impersonation</h3>
            <p className="detect-card-desc">
              Callers posing as government agencies, tax departments, telecom operators, law enforcement, or enterprise IT desks.
            </p>
          </div>

          {/* 5. AI Voice Cloning */}
          <div className="detect-card">
            <div className="detect-card-header">
              <div className="detect-icon-box text-teal-600 bg-teal-50 border border-teal-200">
                <Activity size={20} />
              </div>
              <span className="detect-severity-badge badge-severe">Synthetic Audio</span>
            </div>
            <h3 className="detect-card-title">AI Voice Cloning</h3>
            <p className="detect-card-desc">
              Synthetic vocoder artifacts, deepfake speech patterns, voice conversion algorithms, and unnatural acoustic prosody.
            </p>
          </div>

          {/* 6. Urgency & Psychological Coercion */}
          <div className="detect-card">
            <div className="detect-card-header">
              <div className="detect-icon-box text-orange-600 bg-orange-50 border border-orange-200">
                <AlertTriangle size={20} />
              </div>
              <span className="detect-severity-badge badge-high">Behavioral Vector</span>
            </div>
            <h3 className="detect-card-title">Urgency &amp; Psychological Coercion</h3>
            <p className="detect-card-desc">
              Manufactured panic, secrecy demands, immediate countdowns, and isolation tactics designed to bypass rational verification.
            </p>
          </div>
        </div>
      </section>

      {/* 4. CANONICAL 6-STAGE HOW IT WORKS DETECTION PIPELINE */}
      <section className="pipeline-section">
        <div className="section-head-center mb-5">
          <span className="section-pretitle">Detection Pipeline</span>
          <h2 className="section-main-title">How Voice Shield Analyzes a Call</h2>
          <p className="section-main-desc">
            A synchronized multi-signal pipeline executing real-time voice activity detection, acoustic anti-spoofing, and contextual intent scoring.
          </p>
        </div>

        <div className="canonical-pipeline-grid">
          {/* Stage 1 */}
          <div className="pipeline-flow-card">
            <div className="pipeline-card-top">
              <span className="pipeline-step-pill">Stage 01</span>
              <div className="pipeline-icon text-blue-700 bg-blue-50 border border-blue-200">
                <Waves size={18} />
              </div>
            </div>
            <h3 className="pipeline-title">Audio Ingestion</h3>
            <p className="pipeline-desc">
              Continuous 16 kHz stream ingestion from live microphone or uploaded call recording with noise filtering.
            </p>
          </div>

          {/* Stage 2 */}
          <div className="pipeline-flow-card">
            <div className="pipeline-card-top">
              <span className="pipeline-step-pill">Stage 02</span>
              <div className="pipeline-icon text-blue-700 bg-blue-50 border border-blue-200">
                <Radio size={18} />
              </div>
            </div>
            <h3 className="pipeline-title">Speech Detection / VAD</h3>
            <p className="pipeline-desc">
              Energy-based Voice Activity Detection separates active voiced speech from silence and background artifacts.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="pipeline-flow-card">
            <div className="pipeline-card-top">
              <span className="pipeline-step-pill">Stage 03</span>
              <div className="pipeline-icon text-teal-700 bg-teal-50 border border-teal-200">
                <AudioWaveform size={18} />
              </div>
            </div>
            <h3 className="pipeline-title">Voice Authenticity</h3>
            <p className="pipeline-desc">
              Acoustic neural transformers evaluate vocoder spectrograms and phase continuity to detect AI-cloned speech.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="pipeline-flow-card">
            <div className="pipeline-card-top">
              <span className="pipeline-step-pill">Stage 04</span>
              <div className="pipeline-icon text-indigo-700 bg-indigo-50 border border-indigo-200">
                <ShieldAlert size={18} />
              </div>
            </div>
            <h3 className="pipeline-title">Scam Intelligence</h3>
            <p className="pipeline-desc">
              Linguistic algorithms classify conversational commands, digital arrest claims, OTP harvesting, and coercion.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="pipeline-flow-card">
            <div className="pipeline-card-top">
              <span className="pipeline-step-pill">Stage 05</span>
              <div className="pipeline-icon text-purple-700 bg-purple-50 border border-purple-200">
                <Sliders size={18} />
              </div>
            </div>
            <h3 className="pipeline-title">Risk Fusion</h3>
            <p className="pipeline-desc">
              Deterministic fusion combines independent acoustic and conversational risk weights with consistency floors.
            </p>
          </div>

          {/* Stage 6 */}
          <div className="pipeline-flow-card highlight-stage">
            <div className="pipeline-card-top">
              <span className="pipeline-step-pill pill-emerald">Stage 06</span>
              <div className="pipeline-icon text-emerald-700 bg-emerald-50 border border-emerald-200">
                <ShieldCheck size={18} />
              </div>
            </div>
            <h3 className="pipeline-title">Threat Assessment</h3>
            <p className="pipeline-desc">
              Outputs a calibrated 0–100 threat score, verified scam category, and actionable defense guidance.
            </p>
          </div>
        </div>
      </section>

      {/* 5. SECURITY & PRIVACY PRINCIPLES */}
      <section className="security-principles-section">
        <div className="section-head-center mb-5">
          <span className="section-pretitle">Trust &amp; Transparency</span>
          <h2 className="section-main-title">Security &amp; Privacy Principles</h2>
          <p className="section-main-desc">
            Architected for zero biometric lock-in, independent multi-signal evaluation, and strict ephemeral privacy.
          </p>
        </div>

        <div className="principles-grid">
          <div className="principle-card">
            <div className="principle-icon-box text-blue-700 bg-blue-50 border border-blue-200">
              <Fingerprint size={22} />
            </div>
            <div className="principle-text">
              <h3 className="principle-title">No Voice Registration Required</h3>
              <p className="principle-desc">
                Operates instantly on any call without requiring prior biometric enrollment, reference samples, or user voiceprint registration.
              </p>
            </div>
          </div>

          <div className="principle-card">
            <div className="principle-icon-box text-emerald-700 bg-emerald-50 border border-emerald-200">
              <Layers size={22} />
            </div>
            <div className="principle-text">
              <h3 className="principle-title">Multi-Signal Analysis</h3>
              <p className="principle-desc">
                Evaluates conversational intent and acoustic authenticity as separate signals—ensuring authentic human fraudsters are never misclassified as safe.
              </p>
            </div>
          </div>

          <div className="principle-card">
            <div className="principle-icon-box text-indigo-700 bg-indigo-50 border border-indigo-200">
              <Lock size={22} />
            </div>
            <div className="principle-text">
              <h3 className="principle-title">Privacy-Focused Processing</h3>
              <p className="principle-desc">
                Zero commercial data tracking, advertising hooks, or external voice profiling. Analysis occurs strictly within your active deployment.
              </p>
            </div>
          </div>

          <div className="principle-card">
            <div className="principle-icon-box text-teal-700 bg-teal-50 border border-teal-200">
              <ShieldCheck size={22} />
            </div>
            <div className="principle-text">
              <h3 className="principle-title">Ephemeral Session Analysis</h3>
              <p className="principle-desc">
                Audio stream chunks and live transcript segments are held temporarily in-memory during evaluation and discarded when monitoring concludes.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. CLEAR CALL TO ACTION */}
      <section className="bottom-cta-banner">
        <div className="bottom-cta-inner">
          <h2 className="bottom-cta-title">START PROTECTING YOUR CONVERSATIONS</h2>
          <p className="bottom-cta-desc">
            Upload an existing call recording for forensic analysis or start live monitoring for real-time protection.
          </p>
          <div className="bottom-cta-actions">
            <button className="bottom-cta-btn-primary" onClick={() => onNavigate("/analyze")}>
              <Activity size={16} />
              <span>Analyze a Call</span>
            </button>
            <button className="bottom-cta-btn-secondary" onClick={() => onNavigate("/live")}>
              <Radio size={16} />
              <span>Start Live Monitoring</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
