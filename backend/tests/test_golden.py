from __future__ import annotations

from backend.app.engine.forecast import forecast_cash_flow, optimize_plan, cost_of_waiting


def test_base_forecast_can_run():
    result = forecast_cash_flow("base")
    assert result["ending_cash"] >= 0
    assert result["min_balance"] <= result["ending_cash"]


def test_optimizer_returns_plan():
    plan = optimize_plan("base", "2026-10-12")
    assert "feasible" in plan
    assert "total_cost" in plan


def test_waiting_cost_is_monotonic():
    costs = cost_of_waiting("base")
    assert len(costs) >= 2
    assert costs[0]["total_cost"] <= costs[1]["total_cost"]
