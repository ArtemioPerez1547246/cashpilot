"""End-to-end checks of the API, agent tools, verifier, approval queue and monitor."""
import pytest
from fastapi.testclient import TestClient

from app import monitor
from app.agent.verifier import verify
from app.main import app

c = TestClient(app)


@pytest.fixture(autouse=True)
def clean():
    c.post("/api/demo/reset")
    yield


def test_health_reports_provider():
    r = c.get("/api/health").json()
    assert r["ok"] and r["model_provider"] == "stub"


def test_overview_normal_week_is_safe():
    f = c.get("/api/overview").json()["forecast"]
    assert (f["ending_cash"], f["min_balance"], f["min_date"]) == (2000, 1800, "2026-10-16")


def test_simulate_freezer_deferral_is_fragile():
    f = c.post("/api/simulate", json={"scenario": "disruption", "lever_ids": ["L01"]}).json()
    assert (f["ending_cash"], f["min_balance"]) == (500, 300)


def test_optimize_matches_golden_plan():
    p = c.post("/api/optimize", json={"scenario": "disruption"}).json()
    assert p["feasible"] and p["levers"] == ["L01", "L05B"] and p["total_cost"] == 9.21


def test_cost_of_waiting_rises_then_fails():
    pts = c.get("/api/cost-of-waiting?scenario=disruption").json()
    assert pts[0]["total_cost"] == 9.21 and pts[-1]["feasible"] is False


def test_unknown_ids_are_404_not_500():
    assert c.post("/api/simulate", json={"lever_ids": ["LX"]}).status_code == 404
    assert c.post("/api/events", json={"txn": "T99", "days": 3}).status_code == 404
    assert c.post("/api/actions/A999/approve").status_code == 404


def test_investigation_is_verified_cites_ids_and_shows_trace():
    r = c.post("/api/investigate", json={"scenario": "disruption"}).json()
    assert r["verified"], r["unverified_amounts"]
    assert "T08" in r["cited_txn_ids"]
    assert [t["tool"] for t in r["trace"]][:4] == ["forecast_cash_flow", "find_drivers", "optimize_plan", "cost_of_waiting"]


def test_rerun_never_duplicates_actions_and_approve_is_idempotent():
    c.post("/api/investigate", json={"scenario": "disruption"})
    first = c.get("/api/actions").json()
    c.post("/api/investigate", json={"scenario": "disruption"})
    assert len(c.get("/api/actions").json()) == len(first) == 2
    aid = first[0]["id"]
    assert c.post(f"/api/actions/{aid}/approve").json()["status"] == "approved"
    assert c.post(f"/api/actions/{aid}/reject").json()["status"] == "approved"  # decided once


def test_event_opens_one_alert_with_investigation():
    a = monitor.handle_event("payment_delayed", "T08", 6, sync=True)
    assert a["status"] == "ready" and a["investigation"]["verified"]
    assert monitor.check("again", sync=True) is None  # same problem: no duplicate alert
    assert len(c.get("/api/alerts").json()) == 1


def test_verifier_catches_invented_numbers():
    outputs = [{"min_balance": -2200.0}]
    assert verify("Cash falls to -$2,200.00 [T15]", outputs)["verified"]
    bad = verify("Cash falls to $9,999 [T42]", outputs)
    assert not bad["verified"] and bad["unknown_txn_ids"] == ["T42"]
