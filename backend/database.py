"""SQLite database layer for projects, call logs, and plans."""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "deployment_agent.db")

STAGES = ["Prospect", "Discovery", "Technical", "Pilot", "Legal & Procurement", "Deployment", "Live"]


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'Prospect',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            integration_map TEXT NOT NULL DEFAULT '',
            stakeholder_tracker TEXT NOT NULL DEFAULT '',
            open_questions TEXT NOT NULL DEFAULT '',
            risk_flags TEXT NOT NULL DEFAULT '',
            next_meeting_agenda TEXT NOT NULL DEFAULT '',
            technical_email TEXT NOT NULL DEFAULT '',
            executive_email TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def create_project(client_name: str, industry: str, stage: str = "Prospect") -> dict:
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO projects (client_name, industry, stage) VALUES (?, ?, ?)",
        (client_name, industry, stage),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def get_project(project_id: int) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_project_stage(project_id: int, stage: str) -> Optional[dict]:
    conn = _get_conn()
    conn.execute("UPDATE projects SET stage = ? WHERE id = ?", (stage, project_id))
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_projects() -> list:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_project(project_id: int) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return True


def add_call_log(project_id: int, date: str, notes: str) -> dict:
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO call_logs (project_id, date, notes) VALUES (?, ?, ?)",
        (project_id, date, notes),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM call_logs WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def get_call_logs(project_id: int) -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM call_logs WHERE project_id = ? ORDER BY date ASC",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_plan(project_id: int, integration_map: str, stakeholder_tracker: str,
              open_questions: str, risk_flags: str, next_meeting_agenda: str,
              technical_email: str, executive_email: str) -> dict:
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    existing = conn.execute("SELECT id FROM plans WHERE project_id = ?", (project_id,)).fetchone()
    if existing:
        conn.execute(
            """UPDATE plans SET integration_map = ?, stakeholder_tracker = ?,
               open_questions = ?, risk_flags = ?, next_meeting_agenda = ?,
               technical_email = ?, executive_email = ?, updated_at = ?
               WHERE project_id = ?""",
            (integration_map, stakeholder_tracker, open_questions, risk_flags,
             next_meeting_agenda, technical_email, executive_email, now, project_id),
        )
    else:
        conn.execute(
            """INSERT INTO plans (project_id, integration_map, stakeholder_tracker,
               open_questions, risk_flags, next_meeting_agenda,
               technical_email, executive_email, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, integration_map, stakeholder_tracker, open_questions,
             risk_flags, next_meeting_agenda, technical_email, executive_email, now),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM plans WHERE project_id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row)


def get_plan(project_id: int) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM plans WHERE project_id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
