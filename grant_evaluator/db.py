import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def init_evaluation_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evaluation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id INTEGER NOT NULL,
            criteria_file TEXT,
            criteria_text TEXT,
            rubric TEXT,
            panel_size INTEGER NOT NULL,
            aggregate_score REAL,
            aggregate_summary TEXT,
            compliance_results TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (proposal_id) REFERENCES proposals(id)
        );

        CREATE TABLE IF NOT EXISTS evaluation_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            reviewer_number INTEGER NOT NULL,
            overall_score REAL,
            raw_response TEXT,
            model_used TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES evaluation_runs(id)
        );

        CREATE TABLE IF NOT EXISTS review_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            criterion TEXT NOT NULL,
            score INTEGER NOT NULL,
            strengths TEXT,
            weaknesses TEXT,
            suggestions TEXT,
            FOREIGN KEY (review_id) REFERENCES evaluation_reviews(id)
        );
    """)
    conn.commit()

    # Migration: add compliance_results column if missing
    cols = [row[1] for row in conn.execute("PRAGMA table_info(evaluation_runs)").fetchall()]
    if "compliance_results" not in cols:
        conn.execute("ALTER TABLE evaluation_runs ADD COLUMN compliance_results TEXT")
        conn.commit()

    return conn


def create_run(
    conn: sqlite3.Connection,
    proposal_id: int,
    criteria_file: str | None,
    criteria_text: str | None,
    rubric: list[dict],
    panel_size: int,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO evaluation_runs
            (proposal_id, criteria_file, criteria_text, rubric, panel_size, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (proposal_id, criteria_file, criteria_text, json.dumps(rubric), panel_size, now),
    )
    conn.commit()
    return cursor.lastrowid


def create_review(
    conn: sqlite3.Connection,
    run_id: int,
    reviewer_number: int,
    overall_score: float,
    raw_response: str,
    model_used: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO evaluation_reviews
            (run_id, reviewer_number, overall_score, raw_response, model_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_id, reviewer_number, overall_score, raw_response, model_used, now),
    )
    conn.commit()
    return cursor.lastrowid


def create_review_score(
    conn: sqlite3.Connection,
    review_id: int,
    criterion: str,
    score: int,
    strengths: list[str],
    weaknesses: list[str],
    suggestions: list[str],
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO review_scores (review_id, criterion, score, strengths, weaknesses, suggestions)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            review_id,
            criterion,
            score,
            json.dumps(strengths),
            json.dumps(weaknesses),
            json.dumps(suggestions),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def update_run_aggregate(
    conn: sqlite3.Connection,
    run_id: int,
    aggregate_score: float,
    aggregate_summary: dict,
) -> None:
    conn.execute(
        "UPDATE evaluation_runs SET aggregate_score = ?, aggregate_summary = ? WHERE id = ?",
        (aggregate_score, json.dumps(aggregate_summary), run_id),
    )
    conn.commit()


def update_run_compliance(
    conn: sqlite3.Connection,
    run_id: int,
    compliance_results: list[dict],
) -> None:
    conn.execute(
        "UPDATE evaluation_runs SET compliance_results = ? WHERE id = ?",
        (json.dumps(compliance_results), run_id),
    )
    conn.commit()


def get_latest_run(conn: sqlite3.Connection, proposal_id: int | None = None) -> dict | None:
    if proposal_id:
        row = conn.execute(
            "SELECT * FROM evaluation_runs WHERE proposal_id = ? ORDER BY created_at DESC LIMIT 1",
            (proposal_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM evaluation_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def get_run_reviews(conn: sqlite3.Connection, run_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM evaluation_reviews WHERE run_id = ? ORDER BY reviewer_number",
        (run_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_review_scores(conn: sqlite3.Connection, review_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM review_scores WHERE review_id = ?",
        (review_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_runs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT er.*, p.filename FROM evaluation_runs er "
        "JOIN proposals p ON er.proposal_id = p.id "
        "ORDER BY er.created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]
