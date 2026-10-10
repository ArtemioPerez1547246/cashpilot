from app.engine.forecast import cost_of_waiting, forecast_cash_flow, optimize_plan


def test_forecast_minimum_is_reported_and_non_negative_when_feasible():
    result = forecast_cash_flow("A_normal")
    assert "min_balance" in result
    assert result["min_date"]
    assert result["min_balance"] <= result["ending_cash"]


def test_optimize_returns_valid_plan_shape():
    plan = optimize_plan("A_normal", "2026-10-12")
    assert "decision_date" in plan
    assert "levers" in plan
    assert "total_cost" in plan


def test_cost_of_waiting_is_monotone():
    values = cost_of_waiting("A_normal")
    costs = [entry["total_cost"] for entry in values]
    assert costs[0] <= costs[1] <= costs[2]


def test_disruption_scenario_has_breached_cash():
    result = forecast_cash_flow("B_delayed_receipt")
    assert result["min_balance"] < 0 or result["first_below_reserve"] is not None
