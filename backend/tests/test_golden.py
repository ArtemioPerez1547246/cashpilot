from app.engine.forecast import cost_of_waiting, forecast_cash_flow, optimize_plan


def test_normal_scenario_matches_expected_values():
    result = forecast_cash_flow("A_normal")
    assert result["ending_cash"] == 2000
    assert result["min_balance"] == 1800
    assert result["min_date"] == "2026-10-16"


def test_delayed_receipt_scenario_has_negative_ending():
    result = forecast_cash_flow("B_delayed_receipt")
    assert result["ending_cash"] < 0
    assert result["min_balance"] <= -2200


def test_optimizer_returns_feasible_plan_when_possible():
    plan = optimize_plan("A_normal", "2026-10-12")
    assert "levers" in plan
    assert plan["decision_date"] == "2026-10-12"


def test_waiting_cost_is_non_decreasing():
    costs = cost_of_waiting("A_normal")
    assert costs[0]["total_cost"] <= costs[1]["total_cost"] <= costs[2]["total_cost"]
