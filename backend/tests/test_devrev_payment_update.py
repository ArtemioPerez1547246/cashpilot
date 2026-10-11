"""Website 'customer will pay later': engine numbers, one shift per approval, no duplicate follow-ups."""
from fastapi.testclient import TestClient

from app.devrev_board import store
from app.main import app

c = TestClient(app)
BODY = {"txn": "T08", "new_date": "2026-10-21", "said_by": "Luis Pardo", "channel": "in person",
        "quote": "We'll pay the full amount on the 21st."}


def setup_function():
    c.post("/api/demo/reset")
    store.clear()


def test_preview_uses_engine_numbers_and_writes_nothing():
    p = c.post("/api/devrev/payment-update/preview", json=BODY).json()
    assert p["days_later"] == 6
    assert (p["after"]["lowest"], p["after"]["lowest_date"]) == (-2200, "2026-10-16")
    assert c.get("/api/devrev/follow-ups").json()["total"] == 0
    assert c.get("/api/forecast").json()["min_balance"] == 1800


def test_apply_once_moves_payment_once():
    r1 = c.post("/api/devrev/payment-update/apply", json=BODY).json()
    r2 = c.post("/api/devrev/payment-update/apply", json=BODY).json()
    assert r1["created"] and not r2["created"]
    assert c.get("/api/forecast").json()["min_balance"] == -2200
    assert c.get("/api/devrev/follow-ups").json()["total"] == 1


def test_reset_allows_rehearsal_and_reuses_existing_follow_up():
    c.post("/api/devrev/payment-update/apply", json=BODY)
    c.post("/api/demo/reset")
    r = c.post("/api/devrev/payment-update/apply", json=BODY).json()
    assert not r["created"] and "already tracks" in r["note"]
    assert c.get("/api/forecast").json()["min_balance"] == -2200
    assert c.get("/api/devrev/follow-ups").json()["total"] == 1


def test_bad_inputs_rejected():
    assert c.post("/api/devrev/payment-update/preview", json={**BODY, "txn": "T14"}).status_code == 400
    assert c.post("/api/devrev/payment-update/preview", json={**BODY, "new_date": "2026-10-14"}).status_code == 400
    assert c.post("/api/devrev/payment-update/preview", json={**BODY, "said_by": " "}).status_code == 400
