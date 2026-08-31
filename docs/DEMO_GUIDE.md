# VOICE SHIELD AI — SIH Demo Guide

## What the System Demonstrates

VOICE SHIELD AI runs a **4-signal multi-modal analysis pipeline** in real-time on a single CPU:

| Signal | Weight | Detects |
|:---|:---|:---|
| **Synthetic Voice Detection** | 45% | Neural vocoder artifacts, spectral contrast collapse, dynamic range over-normalization, phase synthesis noise |
| **Biometric Speaker Verification** | 20% | Whether the caller's voice biometrically matches the registered reference speaker |
| **Prosody Anomaly Analysis** | 15% | Unnatural pitch, pause ratio, rhythm, and energy dynamics |
| **Multilingual Social Engineering** | 20% | OTP theft, financial coercion, digital arrest threats (EN / HI / Hinglish / Telugu / Tamil) |

**Strict Rule**: Synthetic voice risk and speaker identity mismatch are always separate, independent signals.

---

## Pre-Demo Setup

### 1. Start the backend
```powershell
cd "C:\Users\Ajay Jana\Desktop\New folder (2)\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### 2. Start the frontend
```powershell
cd "C:\Users\Ajay Jana\Desktop\New folder (2)\frontend"
npm run dev
```

### 3. Open the dashboard
```
http://127.0.0.1:5173
```
Interactive API docs: `http://127.0.0.1:8000/docs`

### 4. Generate demo audio files (one-time setup)
```powershell
cd "C:\Users\Ajay Jana\Desktop\New folder (2)"
.\backend\.venv\Scripts\python.exe .\scripts\generate-demo-audio.py
```

This creates 4 WAV files in `data/sample_audio/`:
| File | Description |
|:---|:---|
| `demo-reference.wav` | Registered CEO reference voice |
| `demo-genuine.wav` | Scenario 1: Clean authentic caller |
| `demo-synthetic.wav` | Scenario 2: AI-cloned voice with vocoder artifacts |
| `demo-call.wav` | Scenario 3: Impostor with financial fraud intent |

---

## 3-Scenario SIH Demo Script

### Scenario 1 — Normal Genuine Call (LOW RISK)

**Expected outcome:** Risk ≤ 30, no active threats, biometric match.

1. Click **"Scenario 1: Clean Genuine Call"** in the demo scenarios bar.
2. Click **"Register Voice"** with `demo-reference.wav` uploaded and speaker ID `executive-ref`.
3. Upload `demo-genuine.wav` and click **"Analyze Audio"**.
4. **Expected results:**
   - Synthetic Voice Risk: ~6% (REAL)
   - Speaker Biometric Match: >90% (AUTHENTIC)
   - Social Engineering Risk: 0% (SAFE)
   - Final Risk Score: LOW (0–30)

---

### Scenario 2 — AI-Cloned Deepfake Voice (HIGH/CRITICAL RISK)

**Expected outcome:** Deepfake detected ≥65%, even though context is neutral.

1. Click **"Scenario 2: AI-Cloned Deepfake Voice"** in the demo scenarios bar.
2. Ensure `executive-ref` reference voice is already registered.
3. Upload `demo-synthetic.wav` and click **"Analyze Audio"**.
4. **Expected results:**
   - Synthetic Voice Risk: ~69% (SYNTHETIC/FAKE)
   - Reasons: "Severe spectral contrast collapse", "Compressed dynamic range", "High ZCR phase noise"
   - Speaker Biometric Match: Match (same voice target was cloned)
   - Social Engineering Risk: 0% (no coercive transcript)
   - Final Risk Score: HIGH (>60) — driven purely by acoustic artifacts

**Key talking point:** The voice passes biometric match because it's a clone, but the AI vocoder artifacts are still detectable acoustically — this is why both signals must be measured independently.

---

### Scenario 3 — Impersonation & Financial Extortion (CRITICAL RISK)

**Expected outcome:** Speaker mismatch + critical social engineering context = CRITICAL.

1. Click **"Scenario 3: Impersonation & Coercion Scam"** in the demo scenarios bar.
2. Ensure `executive-ref` reference voice is already registered.
3. Upload `demo-call.wav` and click **"Analyze Audio"**.
4. **Expected results:**
   - Synthetic Voice Risk: LOW (genuine human impostor, not AI-synthesized)
   - Speaker Biometric Match: MISMATCH (<60%)
   - Social Engineering Risk: CRITICAL (financial transfer + OTP theft + urgency + secrecy)
   - Final Risk Score: CRITICAL (>85)
   - Indicators: "Speaker identity mismatch", "Social Engineering: Financial transfer request", "Social Engineering: Urgency pressure", "Social Engineering: Secrecy instruction"

**Key talking point:** This scenario catches a real human impostor — no deepfake needed. The speaker biometric mismatch + high-pressure coercion transcript drives the CRITICAL alert.

---

## Live Streaming Demo (Chunk Mode)

1. Click **"Live Streaming Chunks"** to start real-time microphone chunk processing.
2. Speak naturally — the rolling analysis bar updates every chunk with:
   - Latest score, rolling EMA average, peak recent risk, trajectory trend (RISING/FALLING/STABLE), chunk latency.
3. Click **"Stop Live Chunks"** when done.

---

## API Endpoints Reference

| Endpoint | Method | Description |
|:---|:---|:---|
| `/api/health` | GET | System health, active model, features supported |
| `/api/audio/analyze` | POST | Full audio file analysis |
| `/api/audio/chunk` | POST | Real-time streaming chunk analysis |
| `/api/speaker/register` | POST | Register reference speaker voice |
| `/api/speaker/verify` | POST | Verify caller against registered voice |
| `/api/context/analyze` | POST | Multilingual social engineering text analysis |
| `/api/analyses` | GET | Audit trail of recent analyses |
| `/api/analysis/{id}/report` | GET | Download Markdown forensic report |
| `/api/ws/live` | WS | Real-time WebSocket alert stream |

---

## Architecture Talking Points for Judges

1. **Why 4 separate signals?** Voice synthesis and speaker impersonation are different attacks. A deepfake voice can match the target (cloning) but still have vocoder artifacts. A real impostor voice won't have artifacts but will fail biometric verification.

2. **Privacy by Design.** Raw voice audio is processed from volatile memory and deleted after each analysis. Reference speakers are stored as non-invertible 64-dimensional mathematical vectors, not recordings.

3. **Indian language support.** The social engineering engine natively parses Hindi (Devanagari script), Hinglish (Roman transliteration), Telugu (Roman), and Tamil (Roman) for cybercrime threat cues — matching how scammers actually speak.

4. **No cloud dependency.** Entire pipeline runs locally on CPU. Can be deployed as an on-premise enterprise appliance or in a government data center with no external data egress.

5. **Explainability.** Every alert includes human-readable evidence: which acoustic feature triggered synthetic detection, which biometric score caused mismatch, and which specific phrase triggered the social engineering alert.

