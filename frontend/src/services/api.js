import axios from "axios";

// Multiple environment variable fallbacks for Vercel / Netlify / Render deployments
const rawApiUrl =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.VITE_RENDER_URL ||
  import.meta.env.VITE_SERVER_URL ||
  import.meta.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000/api";

export const API_BASE_URL = rawApiUrl.replace(/\/+$/, "");

// Log the resolved base URL on startup so it is always visible in DevTools.
const isLocalhost = API_BASE_URL.includes("127.0.0.1") || API_BASE_URL.includes("localhost");
if (isLocalhost && !import.meta.env.DEV) {
  console.warn(
    "[VoiceShield] ⚠️ PRODUCTION NOTICE: VITE_API_BASE_URL is using localhost fallback.\n" +
    "If backend is on Render, configure VITE_API_BASE_URL in your Vercel Project Settings."
  );
} else {
  console.log(`[VoiceShield] Active API Base URL: ${API_BASE_URL}`);
}

export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  (API_BASE_URL.startsWith("https://")
    ? API_BASE_URL.replace(/^https:\/\//, "wss://") + "/ws/live"
    : API_BASE_URL.replace(/^http:\/\//, "ws://") + "/ws/live");

// Explicit timeout tiers according to workload complexity
export const AUDIO_PROCESSING_TIMEOUT = 180000; // 180 seconds (3 min) for heavy acoustic feature extraction, transcription & neural inference
export const TEXT_PROCESSING_TIMEOUT = 45000;   // 45 seconds for NLP intent classification
export const DEFAULT_API_TIMEOUT = 20000;       // 20 seconds for standard telemetry / history
export const HEALTH_CHECK_TIMEOUT = 8000;       // 8 seconds for health checks

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_API_TIMEOUT,
});

// ─── Request interceptor: log every outgoing request URL ────────────────────
apiClient.interceptors.request.use((config) => {
  const fullUrl = `${config.baseURL || API_BASE_URL}${config.url}`;
  console.log(`[VoiceShield] → ${config.method?.toUpperCase()} ${fullUrl}`);
  return config;
});

// ─── Response interceptor: log failures with full detail ────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.config) {
      const fullUrl = `${error.config.baseURL || API_BASE_URL}${error.config.url}`;
      const status = error.response?.status ?? "NO_RESPONSE";
      const msg = error.response?.data?.detail || error.response?.data?.message || error.message;
      console.error(`[VoiceShield] ✗ ${error.config.method?.toUpperCase()} ${fullUrl} → ${status}: ${msg}`);
    }
    return Promise.reject(error);
  }
);

export async function analyzeAudio({ file, transcript, speakerId, signal }) {
  const form = new FormData();
  if (file) form.append("file", file);
  if (transcript) form.append("transcript", transcript);
  if (speakerId) form.append("speaker_id", speakerId);
  const response = await apiClient.post(`/audio/analyze`, form, {
    timeout: AUDIO_PROCESSING_TIMEOUT,
    signal: signal,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function analyzeChunk({ file, transcript, speakerId, signal }) {
  const form = new FormData();
  if (file) form.append("file", file);
  if (transcript) form.append("transcript", transcript);
  if (speakerId) form.append("speaker_id", speakerId);
  const response = await apiClient.post(`/audio/chunk`, form, {
    timeout: 30000,
    signal: signal,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function analyzeContext(transcript, { signal } = {}) {
  const response = await apiClient.post(`/context/analyze`, { transcript }, {
    timeout: TEXT_PROCESSING_TIMEOUT,
    signal: signal,
  });
  return response.data;
}

export async function classifyScam(transcript, { signal } = {}) {
  const response = await apiClient.post(`/scam/classify`, { transcript }, {
    timeout: TEXT_PROCESSING_TIMEOUT,
    signal: signal,
  });
  return response.data;
}

export async function fetchAnalysisHistory(limit = 50) {
  const response = await apiClient.get(`/analyses?limit=${limit}`, {
    timeout: DEFAULT_API_TIMEOUT,
  });
  return response.data.analyses;
}

export async function fetchSingleAnalysis(analysisId) {
  const response = await apiClient.get(`/analysis/${analysisId}`, {
    timeout: DEFAULT_API_TIMEOUT,
  });
  return response.data;
}

export const fetchAnalysisById = fetchSingleAnalysis;

export async function transcribeAudio(file, { signal } = {}) {
  const form = new FormData();
  if (file) form.append("file", file);
  const response = await apiClient.post(`/stt/transcribe`, form, {
    timeout: AUDIO_PROCESSING_TIMEOUT,
    signal: signal,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export function reportUrl(analysisId) {
  return `${API_BASE_URL}/analysis/${analysisId}/report`;
}

export async function registerSpeaker({ file, speakerId }) {
  const form = new FormData();
  if (file) form.append("file", file);
  if (speakerId) form.append("speaker_id", speakerId);
  const response = await apiClient.post(`/speaker/register`, form, {
    timeout: AUDIO_PROCESSING_TIMEOUT,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function saveAnalysisRecord(payload) {
  if (!payload || !payload.analysis_id) return null;

  // 1. Immediately cache in localStorage so History is updated instantly
  try {
    const existing = JSON.parse(localStorage.getItem("voiceshield_history_cache") || "[]");
    const filtered = existing.filter((item) => item.analysis_id !== payload.analysis_id);
    localStorage.setItem("voiceshield_history_cache", JSON.stringify([payload, ...filtered].slice(0, 50)));
  } catch (err) {
    console.warn("LocalStorage cache error:", err);
  }

  // 2. Dispatch event so any open History view updates immediately
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("voiceshield:history_updated", { detail: payload }));
  }

  // 3. Persist to backend database
  try {
    const response = await apiClient.post(`/analysis/save`, payload, {
      timeout: DEFAULT_API_TIMEOUT,
    });
    return response.data;
  } catch (err) {
    console.warn("Failed to persist analysis record to backend database:", err);
    return null;
  }
}

export async function getHealth() {
  const response = await apiClient.get(`/health`, {
    timeout: HEALTH_CHECK_TIMEOUT,
  });
  return response.data;
}
