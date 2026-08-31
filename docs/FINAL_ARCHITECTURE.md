# VOICE SHIELD AI — System Architecture & Technical Specification

> **Smart India Hackathon (SIH) Cybersecurity System**  
> Real-Time Multi-Modal Voice Anti-Spoofing, Biometric Speaker Verification & Social Engineering Detection Engine.

---

## 1. Executive Summary & Pipeline Overview

**VOICE SHIELD AI** is an AI-powered cybersecurity system designed to protect individuals, enterprise call centers, and banking infrastructure from AI-generated deepfake voices, voice cloning attacks, and conversational social engineering extortion.

The end-to-end multi-modal pipeline runs in real-time ($<600\text{ ms}$ latency) with zero reliance on cloud storage for raw voice data (Privacy by Design).

```
                      ┌───────────────────────────────────────┐
                      │          Live Call Audio Stream       │
                      │     (WAV / WebRTC / Telephony)        │
                      └──────────────────┬────────────────────┘
                                         │
                                         ▼
                      ┌───────────────────────────────────────┐
                      │       Multi-Modal Preprocessing       │
                      │  • Multi-format decode (soundfile)    │
                      │  • Resampling to 16 kHz Mono Float32  │
                      │  • Sliding window chunking (0.5-3.0s) │
                      └─────────┬───────────────────┬─────────┘
                                │                   │
       ┌────────────────────────┼───────────────────┴────────────────────────┐
       │                        │                                            │
       ▼                        ▼                                            ▼
┌───────────────┐      ┌───────────────────┐                        ┌───────────────────┐
│ Acoustic/ML   │      │ Biometric Speaker │                        │ Multilingual STT  │
│ Deepfake      │      │ Verification      │                        │ & Social Eng.     │
│ Detection     │      │ (Claimed ID)      │                        │ Engine            │
├───────────────┤      ├───────────────────┤                        ├───────────────────┤
│ • Vocoder     │      │ • 64-D Harmonic   │                        │ • Whisper/Browser │
│   Artifact    │      │   Embedding       │                        │ • 6 Threat Types  │
│   Analysis    │      │ • Cosine Distance │                        │ • EN / HI / TE /  │
│ • Pretrained  │      │ • Calibrated      │                        │   TA / Hinglish   │
│   Anti-Spoof  │      │   Match Score     │                        │ • Coercion Cues   │
│   Adapter     │      │   (0-100)         │                        │                   │
└───────┬───────┘      └─────────┬─────────┘                        └─────────┬─────────┘
        │                        │                                            │
        │                        ▼                                            │
        │              ┌───────────────────┐                                  │
        │              │ Strict Separation │                                  │
        │              │ Synthetic Risk vs │                                  │
        │              │ Identity Mismatch │                                  │
        │              └─────────┬─────────┘                                  │
        │                        │                                            │
        └────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
              ┌─────────────────────────────────────┐
              │    Explainable Risk Fusion Engine   │
              │                                     │
              │  Score = 0.45·DF + 0.20·SPK         │
              │        + 0.15·PROS + 0.20·CTX       │
              │                                     │
              │  • Synergy Boosters                 │
              │  • Points Breakdown                 │
              │  • Dominant Threat Driver           │
              └──────────────────┬──────────────────┘
                                 │
                                 ▼
              ┌─────────────────────────────────────┐
              │   Streaming Chunk Aggregator (EMA)  │
              │  • Rolling Average • Trend Analysis │
              │  • Peak Recent Risk • Latency Track │
              └──────────────────┬──────────────────┘
                                 │
                                 ▼
              ┌─────────────────────────────────────┐
              │   Real-Time Dashboard & Alerts      │
              │  • WebSocket Broadcast              │
              │  • 4 Orthogonal Metric Cards        │
              │  • Audit Trail & Markdown Reports   │
              └─────────────────────────────────────┘
```

---

## 2. Core Subsystems & Components

### A. Deepfake Voice Detection & Adapter Layer
* **Adapter Class**: `PretrainedAntiSpoofAdapter` in `backend/app/services/detection/deepfake.py`.
* **Heuristic Engine**: `ExplainableAcousticDetector` analyzes physical vocoder artifacts:
  - Neural vocoder spectral contrast collapse ($<0.005$)
  - Dynamic headroom over-normalization ($<0.07$)
  - High-frequency phase synthesis artifacts (ZCR $>0.32$)
  - Non-biological continuous voicing ($<6\%$ pauses)
* **Structured Contract**: Always returns `DeepfakeDetectionResult` with `model_name`, `inference_time_ms`, and explainable `reasons`.

### B. Biometric Speaker Verification
* **Algorithm**: `extract_speaker_embedding` computes 64-dimensional spectral harmonic transfer functions and pitch autocorrelation moments.
* **Similarity**: $L_2$ normalized cosine similarity:
  $$\text{Sim}(u, v) = \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$
* **Isolation Rule**: Synthetic voice risk (is this sound made by an AI?) and Speaker identity mismatch (is this caller who they claim to be?) are kept completely orthogonal.

### C. Multilingual Social Engineering Detection
* **Taxonomy**: 6 Indian cybersecurity threat categories:
  1. `CREDENTIAL_OTP`: OTP requests, CVV, password theft.
  2. `FINANCIAL_REQUEST`: Urgent bank transfers, UPI payment demands.
  3. `SECRECY_COERCION`: "Do not tell anyone", "strictly confidential", isolation.
  4. `URGENCY_PRESSURE`: "Immediate action required", "within 10 minutes".
  5. `PROCEDURE_BYPASS`: Bypassing verification protocols, emergency exemptions.
  6. `AUTHORITY_IMPERSONATION`: Police arrest warrants, CBI, RBI, customs threats.
* **Language Support**: Multi-script & Romanized transliteration support:
  - English
  - Hindi (Devanagari: तुरंत पैसे ट्रांसफर करो & Hinglish: *Turant paise bhejo khate me*)
  - Telugu (Romanized: *Ventane dabbu pampandi*)
  - Tamil (Romanized: *Udane panam anuppu*)

### D. Explainable Risk Fusion Engine
* **Mathematical Formula**:
  $$\text{Risk} = 100 \times \left( 0.45 \times P_{\text{deepfake}} + 0.20 \times M_{\text{speaker}} + 0.15 \times A_{\text{prosody}} + 0.20 \times R_{\text{context}} \right)$$
* **Context Dampening**: If speech is clean and conversational, accidental audio glitches are cross-dampened to prevent false alarms.
* **Synergy Booster**: If synthetic voice is accompanied by financial transfer coercion, a synergistic threat bonus ($+12\%$) triggers `CRITICAL` alert status.

### E. Real-Time Audio Chunk Streaming & Latency Tracking
* **Class**: `ChunkStreamAggregator` in `backend/app/services/audio/chunk_processor.py`.
* **Exponential Moving Average (EMA)**:
  $$\bar{S}_t = \alpha \cdot S_t + (1 - \alpha) \cdot \bar{S}_{t-1}, \quad \alpha = 0.35$$
* **Latency Measurement**: Exact millisecond execution timing logged per stage.

---

## 3. API Specification Matrix

| Method | Endpoint | Description | Request Payload | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | System health, active model & features | None | `HealthResponse` |
| `POST` | `/api/audio/analyze` | Full audio file analysis | `multipart/form-data` (`file`, `transcript`, `speaker_id`) | `AnalysisResponse` |
| `POST` | `/api/audio/chunk` | Real-time sliding chunk analysis | `multipart/form-data` (`file`, `transcript`, `speaker_id`) | `AnalysisResponse` (with `rolling_stats`) |
| `POST` | `/api/speaker/register`| Register claimed speaker reference voice | `multipart/form-data` (`file`, `speaker_id`) | `SpeakerRegisterResponse` |
| `POST` | `/api/speaker/verify` | Verify caller against registered voice | `multipart/form-data` (`file`, `speaker_id`) | `SpeakerVerificationResult` |
| `POST` | `/api/context/analyze` | Multilingual social engineering text analysis | `application/json` (`transcript`) | `ContextRiskResponse` |
| `GET` | `/api/analyses` | Historical analysis audit trail | Query params (`limit`, `offset`) | `AnalysisHistoryResponse` |
| `GET` | `/api/analysis/{id}/report`| Markdown forensic audit report download | Path param (`id`) | Raw Markdown Document |
| `WS` | `/api/ws/live` | WebSocket real-time live alert stream | Bidirectional / Broadcast | JSON Event Streams |

---

## 4. Privacy & Ethical Posture

1. **In-Memory Volatile Processing**: Voice audio chunks are processed in volatile memory buffers. Raw audio is not permanently stored unless explicitly requested for forensic evidence.
2. **Biometric Privacy**: Reference speakers are stored as non-invertible 64-dimensional mathematical embedding vectors, not raw voice recordings.
3. **Local / Edge Deployment**: Fully operable on CPU without mandatory cloud egress, complying with Indian data localization guidelines (DPDP Act 2023).
