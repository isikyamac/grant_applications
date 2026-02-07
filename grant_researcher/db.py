import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS grants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT NOT NULL,
            title TEXT,
            agency TEXT,
            description TEXT,
            deadline TEXT,
            url TEXT,
            amount TEXT,
            raw_json TEXT,
            score INTEGER,
            score_reasoning TEXT,
            matched_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source, external_id)
        );

        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            text TEXT,
            file_hash TEXT,
            ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn


def upsert_grant(conn: sqlite3.Connection, grant: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO grants (source, external_id, title, agency, description, deadline, url, amount, raw_json)
        VALUES (:source, :external_id, :title, :agency, :description, :deadline, :url, :amount, :raw_json)
        ON CONFLICT(source, external_id) DO UPDATE SET
            title=excluded.title,
            agency=excluded.agency,
            description=excluded.description,
            deadline=excluded.deadline,
            url=excluded.url,
            amount=excluded.amount,
            raw_json=excluded.raw_json
        """,
        grant,
    )
    conn.commit()


def grant_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM grants").fetchone()[0]


def get_unscored_grants(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM grants WHERE score IS NULL ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def update_score(
    conn: sqlite3.Connection, grant_id: int, score: int, reasoning: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE grants SET score = ?, score_reasoning = ?, matched_at = ? WHERE id = ?",
        (score, reasoning, now, grant_id),
    )
    conn.commit()


def upsert_proposal(
    conn: sqlite3.Connection, filename: str, text: str, file_hash: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO proposals (filename, text, file_hash, ingested_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(filename) DO UPDATE SET
            text=excluded.text,
            file_hash=excluded.file_hash,
            ingested_at=excluded.ingested_at
        """,
        (filename, text, file_hash, now),
    )
    conn.commit()


def get_proposals(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM proposals ORDER BY ingested_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_scored_grants(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM grants WHERE score IS NOT NULL ORDER BY score DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def _parse_deadline(deadline: str) -> datetime | None:
    """Try to parse a deadline string in any of the formats used by our sources."""
    if not deadline:
        return None
    for fmt in (
        "%m/%d/%Y",                    # grants.gov: 03/31/2027
        "%a, %d %b %Y %H:%M:%S %Z",   # eu.funding: Thu, 25 Jul 2024 22:00:00 GMT
        "%a, %d %b %Y %H:%M:%S",       # eu.funding (no tz)
        "%Y-%m-%dZ",                    # ted: 2024-02-16Z
        "%Y-%m-%d%z",                   # ted: 2024-02-16+01:00
        "%Y-%m-%d",                     # ISO date
    ):
        try:
            dt = datetime.strptime(deadline, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def purge_expired_grants(conn: sqlite3.Connection) -> int:
    """Delete grants whose deadline has passed. Returns count of deleted rows."""
    now = datetime.now(timezone.utc)
    rows = conn.execute(
        "SELECT id, deadline FROM grants WHERE deadline IS NOT NULL AND deadline != ''"
    ).fetchall()

    expired_ids = []
    for row in rows:
        dt = _parse_deadline(row["deadline"])
        if dt and dt < now:
            expired_ids.append(row["id"])

    if expired_ids:
        placeholders = ",".join("?" for _ in expired_ids)
        conn.execute(f"DELETE FROM grants WHERE id IN ({placeholders})", expired_ids)
        conn.commit()

    return len(expired_ids)
