"""Monitor: reacts to events with no typed question.

POST /api/events changes the live scenario. The monitor reruns the forecast; if the lowest
balance falls below the reserve it opens an alert and runs the agent's investigation in the
background. A timer also re-checks every RECHECK_SECONDS.
"""
import os
import threading
import time
from datetime import datetime, timezone

from .agent import investigate
from .engine import scenarios as S

RECHECK_SECONDS = int(os.getenv("RECHECK_SECONDS", "600"))
_alerts, _lock = [], threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _investigate_into(alert):
    try:
        result = investigate("live")
        with _lock:
            alert.update(status="ready", investigation=result)
    except Exception as exc:
        with _lock:
            alert.update(status="error", error=f"{type(exc).__name__}: {exc}")


def check(trigger, sync=False):
    f = S.forecast("live")
    if f.min_balance >= S.RESERVE:
        return None
    with _lock:
        if any(a["status"] in ("investigating", "ready") and a["min_balance"] == f.min_balance for a in _alerts):
            return None  # same problem already open: no duplicate alert
        alert = {"id": f"AL{len(_alerts) + 1:03d}", "created_at": _now(), "trigger": trigger,
                 "min_balance": f.min_balance, "min_date": f.min_date,
                 "shortfall_vs_reserve": f.shortfall_vs_reserve, "status": "investigating",
                 "investigation": None}
        _alerts.insert(0, alert)
    if sync:
        _investigate_into(alert)
    else:
        threading.Thread(target=_investigate_into, args=(alert,), daemon=True).start()
    return alert


def handle_event(event_type, txn, days, sync=False):
    if event_type == "payment_delayed":
        S.add_live_change({"op": "shift", "txn": txn, "days": int(days)})
    elif event_type == "payment_cancelled":
        S.add_live_change({"op": "remove", "txn": txn})
    else:
        raise ValueError(f"unknown event type {event_type}")
    return check(f"{event_type} {txn} {days or ''}".strip(), sync=sync)


def get_alerts():
    with _lock:
        return [dict(a) for a in _alerts]


def reset():
    with _lock:
        _alerts.clear()


def start_timer():
    def loop():
        while True:
            time.sleep(RECHECK_SECONDS)
            try:
                check("scheduled re-check")
            except Exception:
                pass
    threading.Thread(target=loop, daemon=True).start()
