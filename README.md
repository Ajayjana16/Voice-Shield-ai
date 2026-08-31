# VOICE SHIELD AI

**Real-Time Multi-Modal Voice Anti-Spoofing & Impersonation Defense System**  
*Smart India Hackathon (SIH) Cybersecurity Prototype*

VOICE SHIELD AI is an AI-powered cybersecurity defense system prototype designed to detect AI-synthesized, cloned, deepfake, or manipulated voices, isolate biometric identity mismatches, and intercept multilingual social engineering extortion during voice calls.

---

## ⚠️ Implementation Status & Model Configuration

### Current Detection Models

**Deepfake / Anti-Spoofing Detection:**
- **Default Mode**: VoiceShield-Acoustic-v2 (Heuristic Fallback)
  - CPU-friendly handcrafted detector using 8 acoustic features
  - Analyzes spectral contrast, dynamic range, zero-crossing rate, pause patterns
  - Works immediately without any model downloads or extra dependencies
- **Optional Pretrained Model**: Configurable via `VOICE_SHIELD_DEEPFAKE_MODEL_ID` environment variable

  **Verified Compatible Models** (standard HuggingFace `Wav2Vec2ForSequenceClassification`, labels: `fake`/`real`):
  | Model ID | Labels | Trained On |
  |---|---|---|
  | `MelodyMachine/Deepfake-audio-detection` ← **RECOMMENDED** | `fake`/`real` | Multiple deepfake datasets |
  | `MelodyMachine/Deepfake-audio-detection-V2` | `fake`/`real` | Multiple deepfake datasets |
  | `Bisher/wav2vec2_ASV_deepfake_audio_detection` | `fake`/`real` | ASVspoof |
  | `Hemgg/Deepfake-audio-detection` | `AIVoice`/`HumanVoice` | Multiple datasets |

  To enable: `VOICE_SHIELD_DEEPFAKE_MODEL_ID=MelodyMachine/Deepfake-audio-detection` in `.env`
  Requires: `pip install transformers torch soundfile scipy numpy`

**Speaker Verification:**
- **Current Implementation**: Handcrafted 64-D spectral embedding baseline
  - Combines sub-band spectral energies, pitch harmonics, formant proxies
  - Cosine similarity matching with calibrated threshold (0.70)
  - **NOT a pretrained speaker recognition model** (no x-vectors, ECAPA-TDNN)
  - For production: integrate speechbrain/spkrec-ecapa-voxceleb or similar

**Multilingual Social Engineering:**
- Keyword/pattern-based detection for 6 fraud categories
- Supports English, Hindi (Devanagari & Hinglish), Telugu, Tamil
- Rule-based system, not deep NLP classification

### Evaluation & Accuracy Claims

**⚠️ IMPORTANT:** The evaluation script (`scripts/evaluate_models.py`) contains TWO distinct sections:
- **Section A - Unit Tests**: Synthetic mathematical tone signals to test detector logic
- **Section B - Real Evaluation**: Fully implemented, runs when audio files are placed in `data/evaluation/`

**Current metrics are from unit tests on synthetic tones, NOT real-world accuracy.**

To perform real evaluation:
1. Download ASVspoof, WaveFake, or similar labeled dataset
2. Place bonafide samples in `data/evaluation/real/`
3. Place spoofed samples in `data/evaluation/synthetic/`
4. Re-run evaluation script — results auto-saved to `data/evaluation/results/`


---

## Key Highlights & Innovations

1. **Multi-Modal Signal Fusion**: Fuses 4 orthogonal intelligence signals into an explainable 0–100 Impersonation Risk Score:
   - **Synthetic Voice Detection ($45\%$)**: Vocoder artifact analysis, spectral contrast collapse, dynamic headroom over-smoothing, and high-frequency phase synthesis anomalies.
   - **Biometric Speaker Verification ($20\%$)**: 64-dimensional spectral harmonic transfer function & pitch moments with $L_2$ normalized cosine similarity.
   - **Prosody Anomaly Analysis ($15\%$)**: Rhythm, pitch drift, and conversational pause continuity.
   - **Multilingual Social Engineering ($20\%$)**: 6 Indian cybersecurity threat categories supporting English, Hindi (Devanagari & Hinglish), Telugu, and Tamil.
2. **Strict Signal Separation**: Explicit separation between *A. Synthetic Voice Risk* (is the voice AI-synthesized?) and *B. Speaker Identity Mismatch* (is the caller who they claim to be?).
3. **Real-Time Streaming Aggregator**: Exponential Moving Average (EMA) smoothing, sliding window peak risk, trajectory trend analysis (`RISING`/`FALLING`/`STABLE`), and latency tracking.
4. **Privacy by Design**: In-memory volatile audio chunk processing without permanent storage of caller voice data (DPDP Act 2023 compliant). Non-invertible mathematical speaker embeddings.
5. **No Cloud Dependency**: Runs completely locally on CPU with optional pretrained neural model integration via Hugging Face.

---

## System Architecture

```text
                      [ Live Call Audio Stream (WAV / Telephony / WebRTC) ]
                                                │
                                                ▼
                                [ Multi-Modal Preprocessing ]
                               • Resampling to 16 kHz Mono
                               • Windowed Sliding Chunking (0.5s - 3.0s)
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │                              │                              │
                 ▼                              ▼                              ▼
    [ Deepfake / Anti-Spoof ]       [ Speaker Verification ]       [ Multilingual STT & Fraud ]
    • Vocoder Artifact Analysis     • 64-D Harmonic Embedding      • 6 Indian Fraud Categories
    • Spectral Contrast Collapse    • Cosine Similarity            • EN, HI, Hinglish, TE, TA
    • Phase Synthesis / ZCR         • Calibrated Match Score       • OTP & Digital Arrest Cues
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                │
                                                ▼
                                 [ Explainable Risk Fusion Engine ]
                                  Risk = 0.45·DF + 0.20·SPK + 0.15·PROS + 0.20·CTX
                                 • Points Breakdown • Dominant Threat Driver
                                                │
                                                ▼
                                 [ Streaming Chunk Aggregator ]
                                 • EMA Smoothing • Trajectory Trend • Latency Track
                                                │
                                                ▼
                                 [ Real-Time Alerts & UI Dashboard ]
                                 • WebSocket Broadcast • 4 Metric Cards • Audit Report
```

---

## 3 SIH Evaluation Scenarios

| Scenario | Voice Type | Claimed ID | Context / Intent | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **1. Genuine Call** | Clean human voice (`demo-genuine.wav`) | Registered CEO (`demo-reference.wav`) | Routine engineering roadmap update | **LOW RISK (0-30)**, Deepfake: Real, Speaker: Match (>90%), Context: Safe |
| **2. Cloned Voice** | AI-generated vocoder voice (`demo-synthetic.wav`) | Registered CEO (`demo-reference.wav`) | Budget confirmation | **HIGH/CRITICAL RISK (>60)**, Deepfake: Fake (>65%), Speaker: Match, Context: Normal |
| **3. Impersonation Fraud** | Impostor voice (`demo-call.wav`) | Registered CEO (`demo-reference.wav`) | Urgent 5 Lakh transfer + OTP demand | **CRITICAL RISK (>85)**, Deepfake: Low, Speaker: Mismatch (<60%), Context: Critical |

---

## Quick Start Guide

### Prerequisites
- Python 3.10, 3.11, or 3.13
- Node.js 18+ and npm
- (Optional) FFmpeg

### 1. Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Open:
- Dashboard: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Benchmark Results (Evaluation Status)

**Unit Test Results (Synthetic Tones):**
- **Deepfake Detection**: 100% accuracy on synthetic tone discrimination (unit test, NOT real-world metric)
  - Latency: ~450-500ms average (depends on model, audio length, CPU load)
  - **Note**: Real deepfake detection requires evaluation on ASVspoof or similar dataset
- **Speaker Verification (Handcrafted Baseline)**: Same speaker similarity 0.999, impostor mismatch 0.667 (unit test only)
- **Multilingual Context**: 100% accuracy on pattern matching unit tests (deterministic, not NLP)

**⚠️  Real Accuracy:** To be established with real labeled datasets. Currently no real-world evaluation data available.

---

## Automated Test Suite

Run the full pytest suite (20 unit and integration tests):
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v
```

---

## Technical Documentation Reference
- Full Technical Architecture: [`docs/FINAL_ARCHITECTURE.md`](file:///docs/FINAL_ARCHITECTURE.md)
- Step-by-Step Demo Guide: [`docs/DEMO_GUIDE.md`](file:///docs/DEMO_GUIDE.md)
- SIH Presentation & Judge Q&A Guide: [`docs/SIH_PRESENTATION.md`](file:///docs/SIH_PRESENTATION.md)

#   V o i c e - S h i e l d - a i  
 