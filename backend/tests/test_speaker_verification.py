import math
from app.models.schemas import AcousticFeatures
from app.services.speaker.verification import (
    extract_speaker_embedding,
    similarity,
    verify_speaker_identity,
)


def test_embedding_normalization_and_similarity():
    features1 = AcousticFeatures(
        duration_seconds=3.0,
        sample_rate=16000,
        rms_energy=0.10,
        zero_crossing_rate=0.08,
        spectral_centroid=1800.0,
        spectral_contrast=0.12,
        pitch_hz=160.0,
        pause_ratio=0.15,
        dynamic_range=0.40,
        byte_entropy=0.55,
    )
    emb1 = extract_speaker_embedding(features=features1)
    assert len(emb1) == 64

    # Embedding L2 norm should be approx 1.0
    norm = math.sqrt(sum(x * x for x in emb1))
    assert abs(norm - 1.0) < 1e-4

    # Cosine similarity with self should be 1.0
    sim_self = similarity(emb1, emb1)
    assert abs(sim_self - 1.0) < 1e-4


def test_speaker_verification_matching():
    features1 = AcousticFeatures(
        duration_seconds=3.0,
        sample_rate=16000,
        rms_energy=0.10,
        zero_crossing_rate=0.08,
        spectral_centroid=1800.0,
        spectral_contrast=0.12,
        pitch_hz=160.0,
        pause_ratio=0.15,
        dynamic_range=0.40,
        byte_entropy=0.55,
    )
    emb1 = extract_speaker_embedding(features=features1)

    result = verify_speaker_identity(emb1, emb1, threshold=0.70)
    assert result.speaker_match is True
    assert result.speaker_match_score >= 95
    assert result.speaker_mismatch < 0.05
    assert result.confidence > 0.5


def test_speaker_verification_mismatch():
    emb1 = [1.0] + [0.0] * 63
    emb2 = [0.0, 1.0] + [0.0] * 62  # Orthogonal vector

    result = verify_speaker_identity(emb1, emb2, threshold=0.70)
    assert result.speaker_match is False
    assert result.speaker_match_score == 0
    assert result.speaker_mismatch == 1.0

