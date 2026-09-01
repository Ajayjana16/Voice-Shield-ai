import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        cursor = connection.execute("PRAGMA table_info(analyses)")
        cols = {row[1]: row for row in cursor.fetchall()}
        if cols and cols.get("final_risk_score", (0, 0, 0, 0))[3] == 1:
            try:
                connection.execute("CREATE TABLE analyses_new (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, risk_level TEXT NOT NULL, final_risk_score INTEGER, payload TEXT NOT NULL)")
                connection.execute("INSERT INTO analyses_new SELECT id, created_at, risk_level, final_risk_score, payload FROM analyses")
                connection.execute("DROP TABLE analyses")
                connection.execute("ALTER TABLE analyses_new RENAME TO analyses")
            except Exception:
                pass
        else:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    final_risk_score INTEGER,
                    payload TEXT NOT NULL
                )
                """
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS speakers (
                speaker_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                reference_path TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )


def save_analysis(payload: dict[str, Any]) -> None:
    analysis_id = payload.get("analysis_id") or payload.get("id")
    if not analysis_id:
        return
    created_at = payload.get("created_at") or datetime.now(UTC).isoformat()
    risk_level = payload.get("risk_level") or payload.get("final_threat_level") or "LOW"
    final_risk_score = payload.get("final_risk_score")
    if final_risk_score is None and "context_risk_score" in payload:
        final_risk_score = payload.get("context_risk_score")

    clean_payload = dict(payload)
    clean_payload["analysis_id"] = analysis_id
    clean_payload["created_at"] = created_at
    clean_payload["risk_level"] = risk_level
    clean_payload["final_risk_score"] = final_risk_score

    with _connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO analyses
                (id, created_at, risk_level, final_risk_score, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                created_at,
                risk_level,
                final_risk_score,
                json.dumps(clean_payload),
            ),
        )


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload FROM analyses WHERE id = ?",
            (analysis_id,),
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def list_analyses(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, created_at, risk_level, final_risk_score, payload
            FROM analyses
            WHERE risk_level != 'PARTIAL_ANALYSIS'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    results = []
    for row in rows:
        try:
            payload = json.loads(row["payload"])
        except (json.JSONDecodeError, TypeError):
            payload = {}
        results.append({
            "analysis_id": row["id"],
            "created_at": row["created_at"],
            "analysis_status": payload.get("analysis_status", "completed"),
            "risk_level": row["risk_level"],
            "final_risk_score": row["final_risk_score"],
            "prediction": payload.get("prediction", "REAL"),
            "voice_authenticity": payload.get("voice_authenticity", "LIKELY_HUMAN"),
            "possible_scam_category": payload.get("possible_scam_category"),
            "model_name": payload.get("model_name", "VoiceShield-Acoustic-v2"),
        })
    return results


def save_speaker(speaker_id: str, created_at: str, reference_path: Path, embedding: list[float]) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO speakers
                (speaker_id, created_at, reference_path, embedding)
            VALUES (?, ?, ?, ?)
            """,
            (speaker_id, created_at, str(reference_path), json.dumps(embedding)),
        )


def get_speaker(speaker_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT speaker_id, created_at, reference_path, embedding FROM speakers WHERE speaker_id = ?",
            (speaker_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "speaker_id": row["speaker_id"],
        "created_at": row["created_at"],
        "reference_path": row["reference_path"],
        "embedding": json.loads(row["embedding"]),
    }
