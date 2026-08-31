import React from "react";
import { Shield, Lock, FileText, CheckCircle2, Radio, Activity, Cpu } from "lucide-react";

export function Footer({ onNavigate }) {
  return (
    <footer className="global-footer-cyber">
      {/* Subtle Background Waveform SVG Pattern */}
      <div className="footer-wave-bg" aria-hidden="true">
        <svg viewBox="0 0 1440 120" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
          <path d="M0,60 C180,90 360,30 540,60 C720,90 900,30 1080,60 C1260,90 1350,45 1440,60 L1440,120 L0,120 Z" fill="rgba(37, 99, 235, 0.03)" />
          <path d="M0,80 C240,40 480,100 720,60 C960,20 1200,90 1440,70" stroke="rgba(56, 189, 248, 0.06)" strokeWidth="1.5" fill="none" />
        </svg>
      </div>

      <div className="footer-container">
        <div className="footer-top-grid">
          {/* Col 1: Brand & Purpose */}
          <div className="footer-brand-col">
            <div className="footer-brand-header">
              <div className="footer-brand-badge">
                <Shield size={16} className="text-blue-400" />
              </div>
              <span className="footer-brand-title">Voice Shield</span>
            </div>
            <p className="footer-brand-desc">
              AI-powered voice security and telecommunication fraud detection. Real-time protection against AI voice clones, digital arrest extortion, OTP theft, and social engineering.
            </p>
            <div className="footer-security-note">
              <Lock size={12} className="text-emerald-400" />
              <span>Local Ingestion • Zero Biometric Storage • Ephemeral Memory</span>
            </div>
          </div>

          {/* Col 2: Navigation Links */}
          <div className="footer-nav-col">
            <h4 className="footer-heading">PLATFORM</h4>
            <ul className="footer-links">
              <li>
                <button className="footer-link-btn" onClick={() => onNavigate("/analyze")}>
                  <Activity size={12} className="inline mr-1.5 opacity-60" />
                  Analyze a Call
                </button>
              </li>
              <li>
                <button className="footer-link-btn" onClick={() => onNavigate("/live")}>
                  <Radio size={12} className="inline mr-1.5 opacity-60 text-blue-400" />
                  Live Microphone Monitor
                </button>
              </li>
              <li>
                <button className="footer-link-btn" onClick={() => onNavigate("/history")}>
                  <FileText size={12} className="inline mr-1.5 opacity-60" />
                  Audit Log &amp; History
                </button>
              </li>
            </ul>
          </div>

          {/* Col 3: Architecture & Security */}
          <div className="footer-nav-col">
            <h4 className="footer-heading">RESOURCES</h4>
            <ul className="footer-links">
              <li>
                <button className="footer-link-btn" onClick={() => onNavigate("/how-it-works")}>
                  <Cpu size={12} className="inline mr-1.5 opacity-60" />
                  System Architecture
                </button>
              </li>
              <li>
                <button className="footer-link-btn" onClick={() => onNavigate("/security")}>
                  <Shield size={12} className="inline mr-1.5 opacity-60" />
                  Security &amp; Privacy
                </button>
              </li>
              <li>
                <button className="footer-link-btn" onClick={() => onNavigate("/how-it-works")}>
                  <Activity size={12} className="inline mr-1.5 opacity-60" />
                  Threat Intelligence
                </button>
              </li>
            </ul>
          </div>

          {/* Col 4: Platform Transparency */}
          <div className="footer-nav-col">
            <h4 className="footer-heading">MULTI-SIGNAL FUSION</h4>
            <p className="footer-transparency-text">
              Voice Shield evaluates acoustic deepfake vocoder dynamics and conversational scam intent as independent, orthogonal dimensions. An authentic human voice can still conduct extortion.
            </p>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom-bar">
          <span className="footer-copy-text">&copy; {new Date().getFullYear()} Voice Shield Security Platform. All rights reserved.</span>
          <div className="footer-legal-links">
            <button className="footer-link-btn text-2xs" onClick={() => onNavigate("/security")}>
              Privacy &amp; Security Policy
            </button>
            <span className="text-slate-600">•</span>
            <button className="footer-link-btn text-2xs" onClick={() => onNavigate("/how-it-works")}>
              Technical Documentation
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
}
