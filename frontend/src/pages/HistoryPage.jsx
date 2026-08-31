import React, { useEffect, useState, useMemo } from "react";
import {
  History,
  Search,
  RefreshCw,
  FileText,
  Clock,
  ChevronRight,
  X,
  ExternalLink,
  Shield,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Radio,
  Activity,
  Layers,
  Sparkles,
  SlidersHorizontal,
  RotateCcw,
} from "lucide-react";

import { fetchAnalysisHistory, fetchAnalysisById, reportUrl } from "../services/api";

// Categorize Threat Level (Conversational Scam Risk)
export function getThreatCategory(row) {
  const isInsuff = row.analysis_status === "insufficient_audio" || row.risk_level === "NO_SPEECH" || row.risk_level === "NOT_ANALYZED";
  const score = row.final_risk_score;
  const level = (row.risk_level || "").toUpperCase();
  const cat = (row.possible_scam_category || "").toLowerCase();

  if (level === "CRITICAL" || (score != null && score >= 75)) return "CRITICAL";
  if (level === "HIGH" || (score != null && score >= 50 && score < 75)) return "HIGH";
  if ((level === "LOW" || level === "MODERATE") && score != null && score >= 25 && score < 50) return "LOW";
  if (score === 0 || (score != null && score < 25) || isInsuff || level === "NO_SPEECH" || cat.includes("routine") || cat.includes("normal") || cat.includes("listening")) {
    return "NO_THREAT";
  }
  return "NO_THREAT";
}

// Categorize Voice Authenticity (Acoustic Deepfake Signal)
export function getVoiceAuthCategory(row) {
  const auth = (row.voice_authenticity || "").toUpperCase();
  const pred = (row.prediction || "").toUpperCase();
  const isInsuff = row.analysis_status === "insufficient_audio" || auth === "INSUFFICIENT_AUDIO" || auth === "NOT_ANALYZED";

  if (auth.includes("SYNTHETIC") || pred === "SYNTHETIC" || pred === "FAKE") {
    return "SYNTHETIC";
  }
  if (auth === "INCONCLUSIVE" || auth === "NOT_EVALUATED" || isInsuff || pred === "NOT_ANALYZED") {
    return "INCONCLUSIVE";
  }
  if (auth === "LIKELY_HUMAN" || pred === "REAL" || pred === "GENUINE") {
    return "LIKELY_HUMAN";
  }
  return "INCONCLUSIVE";
}

export function HistoryPage({ onNavigate }) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // Two Independent Filter Dimensions
  const [threatFilter, setThreatFilter] = useState("ALL"); // 'ALL' | 'CRITICAL' | 'HIGH' | 'LOW' | 'NO_THREAT'
  const [voiceAuthFilter, setVoiceAuthFilter] = useState("ALL"); // 'ALL' | 'LIKELY_HUMAN' | 'SYNTHETIC' | 'INCONCLUSIVE'

  const [selectedAnalysis, setSelectedAnalysis] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await fetchAnalysisHistory(50);
      setAnalyses(data || []);
    } catch {
      setAnalyses([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleRowClick(analysisId) {
    try {
      const fullData = await fetchAnalysisById(analysisId);
      setSelectedAnalysis(fullData);
    } catch {
      setSelectedAnalysis(null);
    }
  }

  const handleResetFilters = () => {
    setThreatFilter("ALL");
    setVoiceAuthFilter("ALL");
    setSearchQuery("");
  };

  // Compute Filter Counts
  const filterCounts = useMemo(() => {
    const threatCounts = { ALL: analyses.length, CRITICAL: 0, HIGH: 0, LOW: 0, NO_THREAT: 0 };
    const voiceCounts = { ALL: analyses.length, LIKELY_HUMAN: 0, SYNTHETIC: 0, INCONCLUSIVE: 0 };

    analyses.forEach((row) => {
      const tCat = getThreatCategory(row);
      if (threatCounts[tCat] !== undefined) threatCounts[tCat]++;

      const vCat = getVoiceAuthCategory(row);
      if (voiceCounts[vCat] !== undefined) voiceCounts[vCat]++;
    });

    return { threatCounts, voiceCounts };
  }, [analyses]);

  // Multi-Dimensional Filtering Logic
  const filtered = useMemo(() => {
    return analyses.filter((item) => {
      const tCat = getThreatCategory(item);
      const vCat = getVoiceAuthCategory(item);

      // 1. Search Query
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        item.analysis_id.toLowerCase().includes(q) ||
        (item.risk_level && item.risk_level.toLowerCase().includes(q)) ||
        (item.possible_scam_category && item.possible_scam_category.toLowerCase().includes(q)) ||
        (item.voice_authenticity && item.voice_authenticity.toLowerCase().includes(q)) ||
        (item.prediction && item.prediction.toLowerCase().includes(q));

      if (!matchesSearch) return false;

      // 2. Threat Level Filter
      if (threatFilter !== "ALL" && tCat !== threatFilter) return false;

      // 3. Voice Authenticity Filter
      if (voiceAuthFilter !== "ALL" && vCat !== voiceAuthFilter) return false;

      return true;
    });
  }, [analyses, searchQuery, threatFilter, voiceAuthFilter]);

  const hasActiveFilters = threatFilter !== "ALL" || voiceAuthFilter !== "ALL" || searchQuery.trim() !== "";

  return (
    <div className="history-page-layout">
      {/* 1. Page Header */}
      <section className="page-intro-header">
        <div className="history-header-top">
          <div>
            <span className="page-pretitle">AUDIT LOG &amp; VERIFICATION ARCHIVE</span>
            <h1 className="page-headline">Analysis History &amp; Records</h1>
            <p className="page-subheadline">
              Review previous call security evaluations with independent filtering for Conversational Threat Level and Acoustic Voice Authenticity.
            </p>
          </div>
          <button
            type="button"
            className="secondary-btn"
            onClick={loadHistory}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? "spin-icon" : ""} />
            <span>Refresh Records</span>
          </button>
        </div>
      </section>

      {/* 2. Explanatory Dual-Dimension Banner */}
      <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-lg mb-4 text-xs text-slate-700 flex items-start gap-3">
        <Layers size={18} className="text-blue-700 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <strong className="text-blue-900 font-bold uppercase tracking-wider block mb-0.5">
            Two Independent Security Dimensions
          </strong>
          <p className="leading-relaxed text-slate-600">
            <strong>Threat Level</strong> evaluates whether the caller is demanding OTPs, impersonating police, or conducting extortion.{" "}
            <strong>Voice Authenticity</strong> evaluates acoustic deepfake vocoder artifacts. A call with a <em>Likely Human</em> voice can still be a <em>Critical Scam</em>.
          </p>
        </div>
      </div>

      {/* 3. Multi-Dimensional Filter Control Panel */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs mb-4 space-y-3">
        {/* Search Row */}
        <div className="flex justify-between items-center flex-wrap gap-3">
          <div className="search-input-wrap flex-1 min-w-[280px]">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              className="search-input text-xs"
              placeholder="Search by Analysis ID, threat category, voice signal..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              className="subtle-link-btn text-xs flex items-center gap-1 text-slate-500 hover:text-red-700"
              onClick={handleResetFilters}
            >
              <RotateCcw size={12} />
              <span>Reset All Filters</span>
            </button>
          )}
        </div>

        {/* Filter Group 1: Threat Assessment (Conversational Scam Intent) */}
        <div className="flex items-center flex-wrap gap-2 pt-2 border-t border-slate-100">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider w-36 flex-shrink-0">
            Threat Level:
          </span>
          <div className="flex items-center flex-wrap gap-1.5">
            {[
              { id: "ALL", label: "All Threat Levels" },
              { id: "CRITICAL", label: "Critical Risk" },
              { id: "HIGH", label: "High Risk" },
              { id: "LOW", label: "Low Risk" },
              { id: "NO_THREAT", label: "No Threat" },
            ].map((lvl) => {
              const count = filterCounts.threatCounts[lvl.id] ?? 0;
              const isActive = threatFilter === lvl.id;
              return (
                <button
                  key={lvl.id}
                  type="button"
                  className={`filter-pill-btn ${isActive ? "filter-active" : ""}`}
                  onClick={() => setThreatFilter(lvl.id)}
                >
                  <span>{lvl.label}</span>
                  <span className="text-2xs opacity-75 font-mono ml-1">({count})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Filter Group 2: Voice Authenticity (Acoustic Deepfake Analysis) */}
        <div className="flex items-center flex-wrap gap-2 pt-2 border-t border-slate-100">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider w-36 flex-shrink-0">
            Voice Authenticity:
          </span>
          <div className="flex items-center flex-wrap gap-1.5">
            {[
              { id: "ALL", label: "All Voice Types" },
              { id: "LIKELY_HUMAN", label: "Likely Human" },
              { id: "SYNTHETIC", label: "Synthetic / Cloned" },
              { id: "INCONCLUSIVE", label: "Inconclusive / No Audio" },
            ].map((lvl) => {
              const count = filterCounts.voiceCounts[lvl.id] ?? 0;
              const isActive = voiceAuthFilter === lvl.id;
              return (
                <button
                  key={lvl.id}
                  type="button"
                  className={`filter-pill-btn ${isActive ? "filter-active" : ""}`}
                  onClick={() => setVoiceAuthFilter(lvl.id)}
                >
                  <span>{lvl.label}</span>
                  <span className="text-2xs opacity-75 font-mono ml-1">({count})</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Results Header Status */}
      <div className="flex justify-between items-center text-xs text-slate-500 mb-2 px-1">
        <span>
          Showing <strong>{filtered.length}</strong> of <strong>{analyses.length}</strong> evaluation records
        </span>
        {hasActiveFilters && (
          <span className="text-primary-700 font-semibold">Active Filter Mode</span>
        )}
      </div>

      {/* 4. Main Data Table */}
      <div className="history-table-container">
        <div className="table-responsive-box">
          <table className="audit-full-table">
            <thead>
              <tr>
                <th>Date &amp; Time</th>
                <th>Analysis ID</th>
                <th>Voice Authenticity</th>
                <th>Scam Category</th>
                <th>Risk Score</th>
                <th>Threat Level</th>
                <th>Session Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="empty-row">
                    Loading historical evaluation records...
                  </td>
                </tr>
              ) : filtered.length > 0 ? (
                filtered.map((row) => {
                  const isInsuff = row.analysis_status === "insufficient_audio" || row.risk_level === "NO_SPEECH";
                  const tCat = getThreatCategory(row);
                  const vCat = getVoiceAuthCategory(row);

                  return (
                    <tr
                      key={row.analysis_id}
                      onClick={() => handleRowClick(row.analysis_id)}
                      style={{ cursor: "pointer" }}
                    >
                      {/* 1. Date & Time */}
                      <td className="text-slate-500 text-xs whitespace-nowrap">
                        {row.created_at ? new Date(row.created_at).toLocaleString() : "Unknown"}
                      </td>

                      {/* 2. Analysis ID */}
                      <td className="mono-id text-xs font-semibold">{row.analysis_id.slice(0, 10)}...</td>

                      {/* 3. Voice Authenticity Dimension */}
                      <td>
                        <span className={`status-pill-subtle ${vCat === "SYNTHETIC" ? "pill-danger" : vCat === "LIKELY_HUMAN" ? "pill-safe" : "pill-neutral"}`}>
                          {vCat === "SYNTHETIC"
                            ? "Synthetic / Cloned"
                            : vCat === "LIKELY_HUMAN"
                            ? "Likely Human"
                            : isInsuff
                            ? "No Audio"
                            : "Inconclusive"}
                        </span>
                      </td>

                      {/* 4. Scam Category */}
                      <td className="text-xs font-medium text-slate-800">
                        {isInsuff ? "—" : row.possible_scam_category || "Routine / Normal Call"}
                      </td>

                      {/* 5. Threat Score */}
                      <td>
                        <strong className={isInsuff || row.final_risk_score == null ? "text-slate-400" : tCat === "CRITICAL" ? "text-red-700" : tCat === "HIGH" ? "text-red-600" : tCat === "LOW" ? "text-amber-700" : "text-emerald-700"}>
                          {isInsuff || row.final_risk_score == null ? "—" : `${row.final_risk_score} / 100`}
                        </strong>
                      </td>

                      {/* 6. Threat Level Dimension */}
                      <td>
                        <span className={`risk-text-tag level-${tCat.toLowerCase().replace("_", "")}`}>
                          {tCat === "CRITICAL"
                            ? "CRITICAL RISK"
                            : tCat === "HIGH"
                            ? "HIGH RISK"
                            : tCat === "LOW"
                            ? "LOW RISK"
                            : "NO THREAT"}
                        </span>
                      </td>

                      {/* 7. Session Status */}
                      <td>
                        <span className={`status-pill-subtle ${isInsuff ? "pill-neutral" : "pill-safe"}`}>
                          {isInsuff ? "No Speech" : "Completed"}
                        </span>
                      </td>

                      {/* 8. Actions */}
                      <td>
                        <button
                          type="button"
                          className="subtle-link-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRowClick(row.analysis_id);
                          }}
                        >
                          <span>Inspect</span>
                          <ChevronRight size={11} />
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={8} className="empty-row">
                    No records match the selected Threat Level &amp; Voice Authenticity filters. Try adjusting your filter selection.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Comprehensive Audit Detail Modal */}
      {selectedAnalysis && (
        <div className="modal-backdrop" onClick={() => setSelectedAnalysis(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-wrap">
                <Shield size={18} className="text-blue-700" />
                <h3>Analysis Details: {selectedAnalysis.analysis_id?.slice(0, 12)}...</h3>
              </div>
              <button
                type="button"
                className="close-btn"
                onClick={() => setSelectedAnalysis(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {/* Dual Metric Summary Grid */}
              <div className="modal-summary-grid">
                {/* Metric 1: Threat Assessment */}
                <div className="modal-stat-box">
                  <span className="stat-k">Conversational Threat Level</span>
                  <strong className={`text-base font-bold level-${(selectedAnalysis.risk_level || "low").toLowerCase().replace(" risk", "").replace("_", "")}`}>
                    {selectedAnalysis.analysis_status === "insufficient_audio" ? "No Speech Detected" : `${selectedAnalysis.risk_level || "LOW"} RISK (${selectedAnalysis.final_risk_score ?? "--"}/100)`}
                  </strong>
                </div>

                {/* Metric 2: Voice Authenticity */}
                <div className="modal-stat-box">
                  <span className="stat-k">Voice Authenticity (Acoustic)</span>
                  <span className="text-sm font-semibold text-slate-800">
                    {selectedAnalysis.analysis_status === "insufficient_audio"
                      ? "Skipped (No Audio)"
                      : `${selectedAnalysis.voice_authenticity ? selectedAnalysis.voice_authenticity.replace("_", " ") : "Likely Human"} (${Math.round((selectedAnalysis.deepfake_probability || 0) * 100)}% Synthetic)`}
                  </span>
                </div>

                {/* Metric 3: Scam Category */}
                <div className="modal-stat-box">
                  <span className="stat-k">Identified Scam Category</span>
                  <strong className="text-sm font-semibold text-slate-900">
                    {selectedAnalysis.possible_scam_category || "Routine / Normal Call"}
                  </strong>
                  {selectedAnalysis.scam_category_confidence && (
                    <span className="text-2xs text-slate-500 block mt-0.5">Confidence: {selectedAnalysis.scam_category_confidence}</span>
                  )}
                </div>

                {/* Metric 4: Context Risk Score */}
                <div className="modal-stat-box">
                  <span className="stat-k">Conversational Intent Score</span>
                  <span className="text-sm font-medium text-slate-700">
                    {selectedAnalysis.context_risk != null ? `${Math.round(selectedAnalysis.context_risk * 100)}% Risk Confidence` : "Evaluated"}
                  </span>
                </div>
              </div>

              {selectedAnalysis.risk_reasoning && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-slate-700">
                  <strong className="text-blue-900 block mb-0.5">Security Assessment Rationale:</strong>
                  <span>{selectedAnalysis.risk_reasoning}</span>
                </div>
              )}

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
                <strong className="text-slate-800 block mb-0.5">Recommended Defense Action:</strong>
                <span className="text-slate-600 leading-relaxed">{selectedAnalysis.recommendation}</span>
              </div>

              {selectedAnalysis.transcript && (
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-semibold text-slate-700">Evaluated Conversation Transcript:</span>
                  <p className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 italic font-mono leading-relaxed max-h-36 overflow-y-auto">
                    &quot;{selectedAnalysis.transcript}&quot;
                  </p>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <span className="text-xs text-slate-500 font-mono">
                {selectedAnalysis.created_at ? new Date(selectedAnalysis.created_at).toLocaleString() : ""}
              </span>
              <div className="flex items-center gap-2">
                <a
                  href={reportUrl(selectedAnalysis.analysis_id)}
                  target="_blank"
                  rel="noreferrer"
                  className="report-download-link"
                >
                  <FileText size={13} />
                  <span>Download Markdown Report</span>
                  <ExternalLink size={11} />
                </a>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => setSelectedAnalysis(null)}
                >
                  <span>Close</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
