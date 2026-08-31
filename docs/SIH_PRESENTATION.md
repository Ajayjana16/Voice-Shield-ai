# SIH Presentation Notes

## Problem

Voice cloning and AI speech generation can impersonate trusted people during calls. The risk is highest when the caller asks for money transfers, OTPs, credentials, confidential data, or procedure bypasses.

## Proposed Solution

VOICE SHIELD AI is a real-time risk console that analyzes the audio signal, claimed speaker identity, and call context before a sensitive action is approved.

## System Modules

- Audio input: file upload, microphone recording, and live chunk processing.
- Audio preprocessing: WAV parsing, mono conversion, feature extraction, and temporary file handling.
- Synthetic speech detection: CPU-friendly MVP detector with a clean boundary for pretrained anti-spoofing models.
- Prosody analysis: pitch, pause ratio, rhythm proxy, energy dynamics, and artifact cues.
- Speaker verification: separate reference-speaker comparison signal.
- Context detection: transcript analysis for urgency, money transfer, OTP, secrecy, authority, and bypass cues.
- Risk engine: configurable weighted score across audio, prosody, speaker, and context signals.
- Dashboard: live waveform, risk gauge, metrics, threats, and recommended actions.

## Demo Scenario

1. Register `data/sample_audio/demo-reference.wav` as `ceo-demo`.
2. Analyze `data/sample_audio/demo-call.wav` as speaker `ceo-demo`.
3. Use this transcript:

```text
This is urgent. Transfer money now and do not tell anyone. Send the OTP immediately.
```

4. Explain that risk rises because context and identity signals are separate from synthetic speech probability.

## Risk Formula

```text
Final Risk =
0.45 * synthetic_voice_risk
+ 0.15 * prosody_anomaly
+ 0.20 * speaker_mismatch
+ 0.20 * social_engineering_risk
```

Risk bands:

- `0-30`: Low
- `31-60`: Medium
- `61-80`: High
- `81-100`: Critical

## Privacy Position

- Raw call audio is written only to `data/temp` for processing and deleted after analysis.
- SQLite stores scores and analysis metadata.
- Speaker reference samples are stored only when the user registers them.
- Future production design should encrypt reference samples and enforce consent-based retention.

## Limitations

- The default detector is not a forensic-grade pretrained model.
- Performance depends on audio quality and input duration.
- Speaker verification uses MVP acoustic embeddings, not a production biometric model.
- Speech-to-text uses browser support or manually supplied transcript in this MVP.

## Upgrade Path

- Replace `backend/app/services/detection/deepfake.py` with an ASVspoof-trained model adapter.
- Replace `backend/app/services/speaker/verification.py` with ECAPA-TDNN or x-vector embeddings.
- Add Whisper or faster-whisper for server-side transcription on Python 3.11.
- Add authenticated user accounts, encrypted storage, and audit logging.
- Add call-platform integration for real inbound voice streams.
