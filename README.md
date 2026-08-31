````md
# 🛡️ Voice Shield AI — Real-Time Multi-Modal Voice Anti-Spoofing & Scam Detection System

Voice Shield AI is an AI-powered cybersecurity prototype designed to detect AI-synthesized, cloned, deepfake, or manipulated voices while identifying social-engineering and voice-based scam attempts during phone or voice conversations.

The system combines **real-time speech monitoring, voice authenticity analysis, acoustic feature extraction, scam detection, transcript analysis, and multi-signal threat fusion** to generate an explainable security assessment.

---

## 🚀 Key Features

### 🎙️ Real-Time Live Monitoring
- Live microphone monitoring
- Speech activity detection
- Progressive speech transcription
- Real-time audio waveform visualization
- Live threat score updates
- Detection event timeline
- Session finalization and security reporting

### 🔍 Scam & Social Engineering Detection
Detects suspicious conversational patterns such as:

- OTP and verification code requests
- Password and credential theft attempts
- Banking and financial fraud
- Urgency and psychological pressure
- Authority impersonation
- Suspicious payment requests
- Social-engineering tactics

### 🎭 Voice Authenticity Analysis
Evaluates voice characteristics to identify potential:

- AI-generated voices
- Voice cloning
- Synthetic speech artifacts
- Deepfake voice patterns
- Suspicious acoustic behavior
- Voice consistency anomalies

### 📊 Multi-Signal Threat Assessment

Multiple detection signals are combined to generate an overall threat score from **0 to 100**.

| Threat Level | Score |
|---|---|
| 🟢 Low Risk | 0–30 |
| 🟡 Moderate Risk | 31–60 |
| 🟠 High Risk | 61–80 |
| 🔴 Critical Risk | 81–100 |

---

## 🧠 How Voice Shield AI Works

```text
Audio Input
    │
    ▼
Speech Activity Detection
    │
    ▼
Speech-to-Text Processing
    │
    ├──────────────────► Scam & Social Engineering Detection
    │
    ▼
Acoustic Feature Extraction
    │
    ▼
Voice Authenticity Analysis
    │
    ▼
Multi-Signal Threat Fusion
    │
    ▼
Threat Score (0–100)
    │
    ▼
Final Security Assessment Report
````

---

## 🖥️ Application Modules

### 🏠 Home

Provides an overview of the Voice Shield AI platform and its cybersecurity capabilities.

### 🔍 Analyze a Call

Upload an audio recording or provide a conversation transcript for post-call forensic analysis.

The system evaluates:

* Audio characteristics
* Voice authenticity
* Scam indicators
* Social-engineering patterns
* Threat category
* Overall threat score
* Security recommendations

### 🎙️ Live Monitor

Monitor microphone audio in real time.

Features include:

* Live audio waveform
* Speech activity detection
* Progressive transcription
* Real-time threat indicators
* Live threat score
* Detection event history
* Final session security report

### 📜 History

Review previously completed call analysis and monitoring sessions.

---

## 🔬 Detection Capabilities

### 1. Acoustic Voice Analysis

The system analyzes multiple audio characteristics, including:

* Spectral features
* Dynamic range
* Pitch variation
* Speech pauses
* Zero-crossing rate
* Audio energy distribution
* Frequency variation
* Speech consistency

These features help identify potentially synthetic, cloned, or manipulated voice behavior.

### 2. Scam & Social Engineering Detection

Conversation text is analyzed for suspicious patterns and security indicators.

Example patterns include:

* “Tell me the OTP”
* “Share your verification code”
* “Your bank account will be blocked”
* “Act immediately”
* “Send the money now”
* “Do not disconnect the call”

Detected conversational signals contribute to the overall threat assessment.

### 3. Voice Authenticity Evaluation

Voice Shield AI evaluates voice characteristics and can classify results such as:

* Likely Human
* Suspicious
* Inconclusive
* Likely Synthetic

Voice authenticity results are combined with conversational scam indicators to produce a more comprehensive security assessment.

---

## 📊 Example Security Assessment

```text
THREAT LEVEL
CRITICAL RISK

THREAT SCORE
85 / 100

SCAM CATEGORY
OTP & Credential Theft Attempt

VOICE AUTHENTICITY
HIGH CONFIDENCE SYNTHETIC

DETECTED THREAT SIGNALS
• Request for OTP / Verification Code
• Urgency & Psychological Time Pressure
• Synthetic Voice Artifact

RECOMMENDED ACTION
Never share OTPs, passwords, verification codes, or banking credentials.
Disconnect the call and verify the caller using an official communication channel.
```

---

## 🏗️ Project Structure

```text
Voice-Shield-AI/
│
├── frontend/                 # User interface
│   ├── src/
│   └── public/
│
├── backend/                  # Backend API and services
│
├── data/                     # Application datasets
│   ├── evaluation/
│   └── reference_voices/
│
├── models/                   # Machine learning and detection models
│
├── scripts/                  # Training and evaluation scripts
│
├── docs/                     # Project documentation
│
├── .gitignore
│
└── README.md
```

---

## 🛠️ Technology Stack

### Frontend

* React
* JavaScript / TypeScript
* Responsive web interface

### Backend

* Python
* REST API

### AI & Machine Learning

* Audio feature extraction
* Speech processing
* Voice authenticity analysis
* Scam detection
* Natural Language Processing
* Machine learning models

### Data

* Voice datasets
* Audio samples
* Synthetic speech datasets
* Scam conversation datasets
* Evaluation datasets

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Ajayana16/Voice-Shield-ai.git
cd Voice-Shield-ai
```

### 2. Setup the Backend

```bash
cd backend
pip install -r requirements.txt
```

Start the backend:

```bash
python main.py
```

### 3. Setup the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

---

## 🌐 Running the Application

After starting both frontend and backend services, open the frontend in your browser.

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
```

---

## 🧪 Project Status

Voice Shield AI is currently a **cybersecurity and AI prototype** focused on:

* Real-time voice monitoring
* Speech detection and transcription
* Scam detection
* Social-engineering detection
* Voice authenticity analysis
* AI-generated voice detection
* Multi-signal threat assessment
* Explainable security recommendations

---

## 🔮 Future Improvements

* Improved deepfake detection models
* Larger real-world training datasets
* Advanced speaker verification
* Multilingual speech analysis
* Improved real-time inference
* Mobile application support
* Expanded scam detection categories
* Improved ML model accuracy

---

## ⚠️ Disclaimer

Voice Shield AI is a research and prototype project.

Detection results should be treated as **security indicators and risk assessments**, not absolute proof. The system should not be the only basis for critical financial, legal, identity, or security decisions.

---

## 🎯 Project Goal

The goal of Voice Shield AI is to provide an intelligent defense layer against modern voice-based cyber threats by combining:

**Voice Analysis + AI Detection + Scam Intelligence + Threat Scoring**

to help identify potentially dangerous voice conversations and provide actionable security guidance.

---

## 👨‍💻 Author

**Ajayana16**

### 🛡️ Voice Shield AI

AI-powered protection against voice scams, impersonation, synthetic voices, voice cloning, deepfakes, and social-engineering attacks.

⭐ If you find this project useful, consider giving the repository a star!

```
```
