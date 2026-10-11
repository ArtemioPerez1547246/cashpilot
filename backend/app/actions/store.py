"""Approval queue. The agent can only DRAFT actions; a person approves or rejects them.

Idempotency: every action has a key (scenario:lever:target transaction). Drafting the same
key twice returns the existing action, so a re-run never creates a duplicate.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

STATE_DIR = Path(os.getenv("CASHPILOT_STATE_DIR", Path(__file__).resolve().parents[2] / "data"))
DB_PATH = STATE_DIR / "actions.db"


class Action(BaseModel):
    id: str
    idempotency_key: str
    lever_id: str
    type: str
    recipient: str
    subject: str = ""
    body: str = ""
    source_txn_ids: list[str] = Field(default_factory=list)
    status: str = "pending"
    created_at: str = ""


def _db():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)   # explicit transactions below
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS actions (
        id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, lever_id TEXT NOT NULL,
        type TEXT NOT NULL, recipient TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL,
        source_txn_ids TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)""")
    return conn


def _row(r):
    return Action(**{**dict(r), "source_txn_ids": json.loads(r["source_txn_ids"])})


def draft_action(lever_id, action_type, recipient, subject, body, source_txn_ids, scenario="live"):
    key = f"{scenario}:{lever_id}:{','.join(sorted(source_txn_ids)) or '-'}"
    conn = _db()
    try:
        conn.execute("BEGIN IMMEDIATE")          # one writer at a time: no duplicate IDs, no duplicate keys
        row = conn.execute("SELECT * FROM actions WHERE idempotency_key = ?", (key,)).fetchone()
        if row:
            conn.execute("COMMIT")
            return _row(row), False
        n = conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(id, 2) AS INTEGER)), 0) FROM actions").fetchone()[0]
        a = Action(id=f"A{n + 1:03d}", idempotency_key=key, lever_id=lever_id, type=action_type,
                   recipient=recipient, subject=subject, body=body, source_txn_ids=source_txn_ids,
                   created_at=datetime.now(timezone.utc).isoformat())
        conn.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (a.id, a.idempotency_key, a.lever_id, a.type, a.recipient, a.subject, a.body,
                      json.dumps(a.source_txn_ids), a.status, a.created_at))
        conn.execute("COMMIT")
        return a, True
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def list_actions():
    with _db() as conn:
        return [_row(r) for r in conn.execute("SELECT * FROM actions ORDER BY created_at DESC, id DESC")]


def get_action(action_id):
    with _db() as conn:
        r = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        return _row(r) if r else None


def set_status(action_id, status):
    """Approve or reject. Safe to call twice; a decided action is never re-decided."""
    a = get_action(action_id)
    if a is None or a.status != "pending":
        return a
    with _db() as conn:
        conn.execute("UPDATE actions SET status = ? WHERE id = ?", (status, action_id))
    return get_action(action_id)


def clear():
    with _db() as conn:
        conn.execute("DELETE FROM actions")
