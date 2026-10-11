"""The guardrail decides correctly without a model: plan levers only, and a per-tool call limit."""
from app.agent.guardrails import decide

PLAN = {"calls": [{"tool": "optimize_plan"}], "outputs": [{"feasible": True, "levers": ["L01", "L05B"]}]}


def test_draft_needs_a_plan_first():
    assert "optimize_plan first" in decide("draft_action", {"lever_id": "L01"}, {"calls": [], "outputs": []}, {})


def test_only_plan_levers_can_be_drafted():
    assert decide("draft_action", {"lever_id": "L01"}, PLAN, {}) is None
    assert "not in the engine" in decide("draft_action", {"lever_id": "L90"}, PLAN, {})


def test_no_drafts_without_a_safe_plan():
    bad = {"calls": [{"tool": "optimize_plan"}], "outputs": [{"feasible": False, "levers": []}]}
    assert "no safe plan" in decide("draft_action", {"lever_id": "L01"}, bad, {})


def test_call_limit():
    counts = {}
    assert all(decide("forecast_cash_flow", {}, PLAN, counts) is None for _ in range(3))
    assert "Limit reached" in decide("forecast_cash_flow", {}, PLAN, counts)
