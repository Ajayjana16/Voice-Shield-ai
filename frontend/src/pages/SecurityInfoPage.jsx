import React from "react";
import {
  Shield,
  Lock,
  Server,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ArrowRight,
  UserCheck,
  Cpu,
} from "lucide-react";

export function SecurityInfoPage({ onNavigate }) {
  return (
    <div className="security-page-layout">
      {/* Header */}
      <section className="page-intro-header">
        <span className="page-pretitle">TRUST & TRANSPARENCY</span>
        <h1 className="page-headline">Security & Privacy Policy</h1>
        <p className="page-subheadline">
          Voice Shield is built with an explicit privacy-first architecture: local ephemeral audio processing, zero mandatory voice enrollment, transparent fallback execution, and deterministic risk reasoning.
        </p>
      </section>

      {/* 4 Pillars Grid */}
      <div className="security-pillars-grid">
        <div className="security-pillar-card">
          <div className="pillar-icon-box">
            <Lock size={18} />
          </div>
          <h3 className="pillar-title">Ephemeral Audio Processing</h3>
          <p className="pillar-desc">
            Raw audio files submitted for evaluation are held in temporary memory buffers only for the duration of inference, then promptly deleted.
          </p>
        </div>

        <div className="security-pillar-card">
          <div className="pillar-icon-box">
            <Server size={18} />
          </div>
          <h3 className="pillar-title">Local Inference Execution</h3>
          <p className="pillar-desc">
            All feature extractors and acoustic classifiers execute on your local or private deployment instance. Voice data is never transmitted to external third-party AI APIs.
          </p>
        </div>

        <div className="security-pillar-card">
          <div className="pillar-icon-box">
            <UserCheck size={18} />
          </div>
          <h3 className="pillar-title">No Voice Enrollment Needed</h3>
          <p className="pillar-desc">
            Analyze unknown suspicious callers immediately without requiring prior speaker registration or storing sensitive biometric voice templates.
          </p>
        </div>

        <div className="security-pillar-card">
          <div className="pillar-icon-box">
            <FileText size={18} />
          </div>
          <h3 className="pillar-title">Auditable Security Reports</h3>
          <p className="pillar-desc">
            Every analysis produces a structured Markdown audit report with exact signal breakdowns, detected scam indicators, and engine timestamps.
          </p>
        </div>
      </div>

      {/* Data Handling & Boundaries */}
      <section className="security-isolation-card">
        <h2 className="text-base font-semibold text-slate-900 mb-2">Data Retention & Privacy Policy</h2>
        <p className="text-sm text-slate-600 mb-4 leading-relaxed">
          Voice Shield operates under strict data minimization guidelines. We distinguish clearly between ephemeral audio data and structured security audit telemetry.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-md">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={14} className="text-emerald-700" />
              <strong className="text-sm font-semibold text-slate-800">What We Retain in Audit Logs</strong>
            </div>
            <ul className="text-xs text-slate-600 flex flex-col gap-1.5">
              <li>&bull; Ephemeral Analysis ID and timestamp</li>
              <li>&bull; Inferred scam category and confidence rating</li>
              <li>&bull; Calibrated risk score and detected indicator labels</li>
              <li>&bull; Acoustic feature vectors (RMS energy, zero-crossing rate)</li>
            </ul>
          </div>

          <div className="p-4 bg-slate-50 border border-slate-200 rounded-md">
            <div className="flex items-center gap-2 mb-2">
              <Lock size={14} className="text-blue-700" />
              <strong className="text-sm font-semibold text-slate-800">What We Never Do</strong>
            </div>
            <ul className="text-xs text-slate-600 flex flex-col gap-1.5">
              <li>&bull; Never sell, commercialize, or share voice data</li>
              <li>&bull; Never use submitted user audio to train commercial models</li>
              <li>&bull; Never permanently archive uploaded caller audio files</li>
              <li>&bull; Never assign fake or fabricated risk scores to silent audio</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Fallback & System Limitations */}
      <section className="security-isolation-card">
        <h2 className="text-base font-semibold text-slate-900 mb-2">Engine Fallback & System Limitations</h2>
        <div className="text-xs text-slate-600 space-y-3 leading-relaxed">
          <p>
            <strong>Two-Tier Engine Resilience: </strong>
            Voice Shield employs a neural transformer model alongside a deterministic handcrafted acoustic fallback engine (<code className="text-blue-700 font-mono">VoiceShield-Acoustic-v2</code>). If neural model inference is unavailable or fails, the fallback engine automatically engages and marks the audit record accordingly.
          </p>
          <p>
            <strong>System Boundaries & Human Judgment: </strong>
            Voice Shield provides advisory threat evaluations based on acoustic and conversational risk signals. It is designed as an investigative decision-support tool and should be accompanied by standard verification procedures (such as contacting banks or organizations via official independently verified phone numbers).
          </p>
        </div>
      </section>

      {/* Bottom Action */}
      <section className="p-6 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center flex-wrap gap-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Have questions about deployment?</h3>
          <p className="text-xs text-slate-600 mt-0.5">Explore the multi-signal detection pipeline or start evaluating calls in the workspace.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="secondary-btn" onClick={() => onNavigate("/how-it-works")}>
            <span>How It Works</span>
          </button>
          <button className="primary-cta-btn" onClick={() => onNavigate("/analyze")}>
            <span>Analyze a Call</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </section>
    </div>
  );
}
