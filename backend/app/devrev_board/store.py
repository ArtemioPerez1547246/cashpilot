"""DevRev follow-up board: storage for tasks DevRev Computer creates through our MCP connector.

DATA: follow-ups come from synthetic call transcripts written by our team for this demo (DevRev staff said teams
may load their own data). It never touches
ForeCash's Paleteria data, the cash forecast, or the ForeCash action queue (separate database).

Idempotency: every follow-up has a key. Creating the same key twice returns the existing task
(and counts the repeat), so a re-run or a retry after a timeout never makes a duplicate.
Standard library only, so the API container can read it without the MCP SDK installed.
"""
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(os.getenv("CASHPILOT_STATE_DIR", Path(__file__).resolve().parents[2] / "data"))
DB_PATH = STATE_DIR / "devrev_board.db"
STATUSES = ("open", "done")
NOT_DOCUMENTED = "not documented"


def _db():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)  # explicit transactions
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS follow_ups (
        id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL, account TEXT NOT NULL,
        title TEXT NOT NULL, details TEXT NOT NULL, owner TEXT NOT NULL, due_date TEXT NOT NULL,
        sources TEXT NOT NULL, requested_by TEXT NOT NULL, status TEXT NOT NULL,
        repeat_attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    conn.execute("CREATE TABLE IF NOT EXISTS applied_updates (key TEXT PRIMARY KEY, created_at TEXT NOT NULL)")
    return conn


def _row(r):
    d = dict(r)
    d["sources"] = json.loads(d["sources"])
    return d


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def validate(account, title, sources, details="", owner="", due_date="", requested_by=""):
    """Clean a draft. Raises ValueError with a message the caller can act on."""
    account, title = _norm(account), _norm(title)
    if not account:
        raise ValueError("account is required: use the account name or ID from the evidence record")
    if not 3 <= len(title) <= 200:
        raise ValueError("title must be 3-200 characters")
    if len(details or "") > 2000:
        raise ValueError("details must be at most 2000 characters")
    if due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due_date.strip()):
        raise ValueError("due_date must be YYYY-MM-DD as stated in the source, or empty if not documented")
    clean_sources = []
    for s in sources or []:
        s = dict(s)
        ref = _norm(s.get("ref", ""))
        if not ref:
            continue
        clean_sources.append({"ref": ref, "sha256": _norm(s.get("sha256", "")),
                              "lines": _norm(s.get("lines", "")), "quote": _norm(s.get("quote", ""))[:300]})
    if not clean_sources:
        raise ValueError("at least one source reference is required: no follow-up without evidence")
    return {"account": account, "title": title, "details": (details or "").strip(),
            "owner": _norm(owner) or NOT_DOCUMENTED, "due_date": (due_date or "").strip() or NOT_DOCUMENTED,
            "sources": clean_sources, "requested_by": _norm(requested_by) or "unknown"}


def make_key(draft):
    refs = ",".join(sorted(s["ref"].lower() for s in draft["sources"]))
    raw = f"{draft['account'].lower()}|{draft['title'].lower()}|{refs}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def find_by_key(key):
    with _db() as conn:
        r = conn.execute("SELECT * FROM follow_ups WHERE idempotency_key = ?", (key,)).fetchone()
        return _row(r) if r else None


def preview(**fields):
    """Exactly what create would write. Writes nothing."""
    draft = validate(**fields)
    key = make_key(draft)
    existing = find_by_key(key)
    return {"would_create": {**draft, "status": "open"}, "idempotency_key": key,
            "duplicate_of": existing["id"] if existing else None,
            "note": "Preview only; nothing was written. Creating requires the user's approval."}


def create(idempotency_key="", **fields):
    """Create once. Same key again returns the existing task with created=False."""
    draft = validate(**fields)
    key = _norm(idempotency_key) or make_key(draft)
    now = datetime.now(timezone.utc).isoformat()
    conn = _db()
    try:
        conn.execute("BEGIN IMMEDIATE")  # one writer at a time across containers
        r = conn.execute("SELECT * FROM follow_ups WHERE idempotency_key = ?", (key,)).fetchone()
        if r:
            conn.execute("UPDATE follow_ups SET repeat_attempts = repeat_attempts + 1, updated_at = ? "
                         "WHERE id = ?", (now, r["id"]))
            conn.execute("COMMIT")
            return {"follow_up": get(r["id"]), "created": False,
                    "note": "Already exists for this idempotency key; no duplicate was created."}
        n = conn.execute("SELECT COUNT(*) FROM follow_ups").fetchone()[0]
        fid = f"F{n + 1:03d}"
        conn.execute("INSERT INTO follow_ups (id, idempotency_key, account, title, details, owner, due_date, "
                     "sources, requested_by, status, repeat_attempts, created_at, updated_at) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (fid, key, draft["account"], draft["title"], draft["details"], draft["owner"],
                      draft["due_date"], json.dumps(draft["sources"]), draft["requested_by"], "open", 0, now, now))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"follow_up": get(fid), "created": True, "note": "Created on the ForeCash follow-up board."}


def get(follow_up_id):
    with _db() as conn:
        r = conn.execute("SELECT * FROM follow_ups WHERE id = ?", (follow_up_id,)).fetchone()
        return _row(r) if r else None


def list_follow_ups(account="", status="", limit=50, offset=0):
    if status and status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("limit must be 1-100 and offset >= 0")
    q, args = "SELECT * FROM follow_ups WHERE 1=1", []
    if account:
        q += " AND lower(account) LIKE ?"
        args.append(f"%{_norm(account).lower()}%")
    if status:
        q += " AND status = ?"
        args.append(status)
    with _db() as conn:
        total = conn.execute(q.replace("SELECT *", "SELECT COUNT(*)"), args).fetchone()[0]
        rows = conn.execute(q + " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?", args + [limit, offset])
        items = [_row(r) for r in rows]
    return {"follow_ups": items, "total": total,
            "next_offset": offset + limit if offset + limit < total else None}


def set_status(follow_up_id, status):
    """Dashboard only (not exposed to Computer). Safe to repeat."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if get(follow_up_id) is None:
        return None
    with _db() as conn:
        conn.execute("UPDATE follow_ups SET status = ?, updated_at = ? WHERE id = ?",
                     (status, datetime.now(timezone.utc).isoformat(), follow_up_id))
    return get(follow_up_id)


def clear():
    """Tests and manual reset only. Not exposed through MCP or the API."""
    with _db() as conn:
        conn.execute("DELETE FROM follow_ups")


def mark_applied(key):
    """True the first time a website update key is applied (atomic); False on any repeat."""
    with _db() as conn:
        cur = conn.execute("INSERT OR IGNORE INTO applied_updates VALUES (?, ?)",
                           (key, datetime.now(timezone.utc).isoformat()))
        return cur.rowcount == 1


def clear_applied():
    """Called by 'Reset demo' so a rehearsal can apply the same update again."""
    with _db() as conn:
        conn.execute("DELETE FROM applied_updates")


def find_open_match(account, due_date):
    for f in list_follow_ups(account=account, status="open", limit=100)["follow_ups"]:
        if f["due_date"] == due_date:
            return f
    return None


def is_applied(key):
    with _db() as conn:
        return conn.execute("SELECT 1 FROM applied_updates WHERE key = ?", (key,)).fetchone() is not None
