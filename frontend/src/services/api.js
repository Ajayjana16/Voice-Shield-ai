import axios from "axios";

export const API_BASE_URL = "http://127.0.0.1:8000/api";
export const WS_URL = "ws://127.0.0.1:8000/api/ws/live";

// Explicit timeout tiers according to workload complexity
export const AUDIO_PROCESSING_TIMEOUT = 180000; // 180 seconds (3 min) for heavy acoustic feature extraction, transcription & neural inference
export const TEXT_PROCESSING_TIMEOUT = 45000;   // 45 seconds for NLP intent classification
export const DEFAULT_API_TIMEOUT = 20000;       // 20 seconds for standard telemetry / history
export const HEALTH_CHECK_TIMEOUT = 5000;       // 5 seconds for lightweight health checks

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_API_TIMEOUT,
});

export async function analyzeAudio({ file, transcript, speakerId }) {
  const form = new FormData();
  if (file) form.append("file", file);
  if (transcript) form.append("transcript", transcript);
  if (speakerId) form.append("speaker_id", speakerId);
  const response = await apiClient.post(`/audio/analyze`, form, {
    timeout: AUDIO_PROCESSING_TIMEOUT,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function analyzeChunk({ file, transcript, speakerId }) {
  const form = new FormData();
  if (file) form.append("file", file);
  if (transcript) form.append("transcript", transcript);
  if (speakerId) form.append("speaker_id", speakerId);
  const response = await apiClient.post(`/audio/chunk`, form, {
    timeout: 30000,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function analyzeContext(transcript) {
  const response = await apiClient.post(`/context/analyze`, { transcript }, {
    timeout: TEXT_PROCESSING_TIMEOUT,
  });
  return response.data;
}

export async function classifyScam(transcript) {
  const response = await apiClient.post(`/scam/classify`, { transcript }, {
    timeout: TEXT_PROCESSING_TIMEOUT,
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

export async function transcribeAudio(file) {
  const form = new FormData();
  if (file) form.append("file", file);
  const response = await apiClient.post(`/stt/transcribe`, form, {
    timeout: AUDIO_PROCESSING_TIMEOUT,
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

export async function getHealth() {
  const response = await apiClient.get(`/health`, {
    timeout: HEALTH_CHECK_TIMEOUT,
  });
  return response.data;
}
