from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VOICE SHIELD AI"
    api_prefix: str = "/api"
    database_path: Path = Path("../data/voice_shield.sqlite3")
    temp_audio_dir: Path = Path("../data/temp")
    reference_voice_dir: Path = Path("../data/reference_voices")
    medium_threshold: int = 31
    high_threshold: int = 61
    critical_threshold: int = 81
    deepfake_weight: float = 0.45
    prosody_weight: float = 0.15
    speaker_weight: float = 0.20
    context_weight: float = 0.20

    # Pretrained anti-spoofing model from Hugging Face
    # Set via VOICE_SHIELD_DEEPFAKE_MODEL_ID env var (or .env file)
    #
    # Setting to None (default) uses the heuristic fallback (VoiceShield-Acoustic-v2)
    # which requires NO additional dependencies.
    #
    # VERIFIED COMPATIBLE MODELS (Wav2Vec2ForSequenceClassification, labels: fake/real):
    #   MelodyMachine/Deepfake-audio-detection       ← RECOMMENDED (fake/real labels)
    #   MelodyMachine/Deepfake-audio-detection-V2    ← V2 variant (fake/real labels)
    #   Bisher/wav2vec2_ASV_deepfake_audio_detection ← ASV-trained (fake/real labels)
    #   Hemgg/Deepfake-audio-detection               ← (AIVoice/HumanVoice labels)
    #
    # REQUIREMENTS for pretrained model:
    #   pip install transformers torch soundfile scipy numpy
    #
    # HOW TO ENABLE:
    #   Set VOICE_SHIELD_DEEPFAKE_MODEL_ID=MelodyMachine/Deepfake-audio-detection in .env
    #
    # IMPORTANT: Do NOT use generic base models (wavlm-base, wav2vec2-base, hubert-base)
    # without a trained classification head. The loader will block these automatically.
    # If None or model fails to load, falls back to VoiceShield-Acoustic-v2 (heuristic).
    deepfake_model_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="VOICE_SHIELD_")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.temp_audio_dir.mkdir(parents=True, exist_ok=True)
    settings.reference_voice_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
