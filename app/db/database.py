import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.schemas import Lead


def database_path() -> str:
    return os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parents[2] / "data" / "leads.db"))


def connect() -> sqlite3.Connection:
    path = database_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            lead_id TEXT PRIMARY KEY, name TEXT, email TEXT, company TEXT,
            company_size INTEGER, requirements TEXT, current_solution TEXT,
            lead_status TEXT NOT NULL DEFAULT 'new', qualification_reason TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(lead_id) REFERENCES leads(lead_id)
        );
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL,
            scheduled_for TEXT NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'scheduled'
        );
        CREATE TABLE IF NOT EXISTS handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT NOT NULL,
            reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
        );
        """)


def get_lead(lead_id: str) -> Lead | None:
    with connect() as db:
        row = db.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
    return Lead.model_validate(dict(row)) if row else None


def update_lead(lead_id: str, **fields: Any) -> Lead:
    allowed = {"name", "email", "company", "company_size", "requirements", "current_solution", "lead_status", "qualification_reason"}
    updates = {key: value for key, value in fields.items() if key in allowed and value is not None}
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        exists = db.execute("SELECT 1 FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
        if not exists:
            db.execute("INSERT INTO leads (lead_id, created_at, updated_at) VALUES (?, ?, ?)", (lead_id, now, now))
        if updates:
            assignments = ", ".join(f"{key} = ?" for key in updates)
            db.execute(f"UPDATE leads SET {assignments}, updated_at = ? WHERE lead_id = ?", (*updates.values(), now, lead_id))
        else:
            db.execute("UPDATE leads SET updated_at = ? WHERE lead_id = ?", (now, lead_id))
    lead = get_lead(lead_id)
    if lead is None:
        raise RuntimeError(f"Could not load lead {lead_id} after update")
    return lead


def save_message(lead_id: str, role: str, content: str) -> None:
    if role not in {"user", "assistant"}:
        raise ValueError("role must be user or assistant")
    with connect() as db:
        db.execute("INSERT INTO messages (lead_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                   (lead_id, role, content, datetime.now(timezone.utc).isoformat()))


def get_history(lead_id: str, limit: int = 20) -> list[dict[str, str]]:
    with connect() as db:
        rows = db.execute("SELECT role, content FROM messages WHERE lead_id = ? ORDER BY id DESC LIMIT ?", (lead_id, limit)).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def create_followup(lead_id: str, scheduled_for: str, note: str) -> dict[str, Any]:
    with connect() as db:
        cursor = db.execute("INSERT INTO followups (lead_id, scheduled_for, note) VALUES (?, ?, ?)", (lead_id, scheduled_for, note))
    return {"followup_id": cursor.lastrowid, "lead_id": lead_id, "scheduled_for": scheduled_for, "note": note, "status": "scheduled"}


def create_handoff(lead_id: str, reason: str) -> dict[str, Any]:
    with connect() as db:
        cursor = db.execute("INSERT INTO handoffs (lead_id, reason) VALUES (?, ?)", (lead_id, reason))
    return {"handoff_id": cursor.lastrowid, "lead_id": lead_id, "reason": reason, "status": "pending"}


def list_records(table: str, lead_id: str) -> list[dict[str, Any]]:
    if table not in {"followups", "handoffs"}:
        raise ValueError("unsupported record type")
    with connect() as db:
        rows = db.execute(f"SELECT * FROM {table} WHERE lead_id = ? ORDER BY id", (lead_id,)).fetchall()
    return [dict(row) for row in rows]
