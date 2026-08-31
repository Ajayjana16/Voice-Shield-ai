# Phase 1 Setup

This file documents the original Phase 1 setup. The repository now also includes later MVP phases: backend APIs, risk scoring services, dashboard UI, microphone recording, and WebSocket analysis events.

## Recommended Folder Structure

```text
voice-shield-ai/
  backend/
    app/
      api/
      core/
      db/
      models/
      services/
        audio/
        detection/
        prosody/
        risk/
        speaker/
        stt/
    tests/
    requirements.txt
  frontend/
    public/
    src/
      assets/
      components/
      hooks/
      pages/
      services/
    package-plan.json
  data/
    reference_voices/
    sample_audio/
    temp/
  docs/
  models/
  scripts/
  README.md
```

## Module Responsibilities

- `backend/app/api`: REST and WebSocket endpoints.
- `backend/app/core`: configuration, logging, constants, and shared app setup.
- `backend/app/db`: SQLite persistence layer.
- `backend/app/models`: request and response schemas plus database models.
- `backend/app/services/audio`: audio loading, chunking, validation, and preprocessing.
- `backend/app/services/detection`: synthetic speech and deepfake detection.
- `backend/app/services/prosody`: pitch, rhythm, pause, and energy analysis.
- `backend/app/services/risk`: weighted final risk scoring.
- `backend/app/services/speaker`: reference voice registration and speaker verification.
- `backend/app/services/stt`: speech-to-text integration.
- `frontend/src/components`: reusable dashboard UI.
- `frontend/src/pages`: dashboard pages and top-level views.
- `frontend/src/services`: API and WebSocket clients.
- `frontend/src/hooks`: microphone and live analysis hooks.
- `data/temp`: temporary audio processing only.
- `models`: optional local model cache or exported model files.

## Exact Setup Commands

Run from PowerShell in the project root.

```powershell
cd "C:\Users\Ajay Jana\Desktop\New folder (2)"
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If Python 3.11 is not installed:

```powershell
winget install Python.Python.3.11
```

Verify frontend prerequisites:

```powershell
node --version
npm --version
```

Verify optional audio tooling:

```powershell
ffmpeg -version
```

If FFmpeg is not installed:

```powershell
winget install Gyan.FFmpeg
```

## Why This Phase Matters

This layout keeps the MVP modular:

- The deepfake model can be replaced without changing the API.
- Speaker verification remains separate from synthetic speech detection.
- Social engineering detection can work from transcripts without depending on voice identity.
- The dashboard can consume stable JSON responses from the beginning.
- Raw audio can remain temporary while metadata and scores are stored.

## Phase 1 Verification Checklist

- `backend/requirements.txt` exists.
- Backend virtual environment activates.
- Dependencies install successfully.
- `frontend/package.json` contains the dashboard app dependencies.
- `data/temp` exists for temporary processing.
- No API server is expected in Phase 1.
