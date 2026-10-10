from __future__ import annotations

from threading import Lock

actions_store: list[dict] = []
alerts_store: list[dict] = []
_store_lock = Lock()


def create_action(payload: dict) -> dict:
    with _store_lock:
        existing = next((a for a in actions_store if a.get("idempotency_key") == payload.get("idempotency_key")), None)
        if existing:
            return existing
        actions_store.append(payload)
        return payload


def approve_action(action_id: str) -> dict:
    with _store_lock:
        for action in actions_store:
            if action.get("id") == action_id:
                action["status"] = "approved"
                return action
    raise KeyError(f"Action {action_id} not found")


def reject_action(action_id: str) -> dict:
    with _store_lock:
        for action in actions_store:
            if action.get("id") == action_id:
                action["status"] = "rejected"
                return action
    raise KeyError(f"Action {action_id} not found")


def add_alert(alert: dict) -> dict:
    with _store_lock:
        alerts_store.insert(0, alert)
        return alert
