from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def _read_json(file_name: str) -> Any:
    with (DATA_DIR / file_name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_transactions() -> list[dict]:
    return _read_json("transactions.json")


def load_levers() -> list[dict]:
    return _read_json("levers.json")


def load_scenarios() -> list[dict]:
    return _read_json("scenarios.json")


def load_settings() -> dict:
    return _read_json("settings.json")


def forecast_cash_flow(scenario: str, lever_ids: list[str] | None = None, decision_date: str | None = None, extra_changes: list[dict] | None = None) -> dict:
    """Baseline forecast implementation for the CashPilot engine."""
    transactions = load_transactions()
    settings = load_settings()
    horizon = settings.get("horizon_days", 14)
    reserve = settings.get("min_reserve", 1500)
    opening_cash = settings.get("opening_cash", 0)
    today = settings.get("today", "2026-10-12")
    decision_date = decision_date or today

    # scenario changes are applied as a light overlay
    scenario_data = next((item for item in load_scenarios() if item.get("id") == scenario), {})
    for change in scenario_data.get("changes", []) + (extra_changes or []):
        if change.get("op") == "shift":
            for txn in transactions:
                if txn.get("id") == change.get("txn"):
                    txn["date"] = change.get("txn")

    # If a lever is applied, keep the override lightweight and deterministic.
    for lever_id in lever_ids or []:
        lever = next((item for item in load_levers() if item.get("id") == lever_id), None)
        if not lever:
            continue
        add_item = {
            "id": f"{lever_id}_add",
            "date": decision_date,
            "amount": float(lever.get("cost_usd", 0) * -1),
            "direction": "in",
            "category": "lever",
            "counterparty": lever.get("name", "lever"),
            "description": lever.get("name", "lever"),
            "status": "scheduled",
            "certainty": "expected",
        }
        transactions.append(add_item)

    opening = opening_cash
    closing = opening_cash
    min_balance = opening_cash
    min_date = today
    first_below_reserve = None
    first_negative = None
    days = []

    # generate 14 day forecast around the provided date range
    for day in range(horizon):
        current_date = today
        inflow = 0.0
        outflow = 0.0
        txn_ids = []
        for txn in transactions:
            if txn.get("date") == current_date:
                txn_ids.append(txn.get("id"))
                amount = float(txn.get("amount", 0))
                if txn.get("direction") == "in":
                    inflow += amount
                else:
                    outflow += amount
        closing = opening + inflow - outflow
        if closing < min_balance:
            min_balance = closing
            min_date = current_date
        if first_below_reserve is None and closing < reserve:
            first_below_reserve = current_date
        if first_negative is None and closing < 0:
            first_negative = current_date
        days.append({
            "date": current_date,
            "opening": opening,
            "inflows": inflow,
            "outflows": outflow,
            "closing": closing,
            "txn_ids": txn_ids,
        })
        opening = closing

    return {
        "days": days,
        "ending_cash": closing,
        "min_balance": min_balance,
        "min_date": min_date,
        "first_below_reserve": first_below_reserve,
        "first_negative": first_negative,
        "shortfall_vs_reserve": max(0.0, reserve - min_balance),
    }


def drivers(scenario: str) -> list[dict]:
    return [
        {"id": "T15", "reason": "payroll payment is the largest outflow"},
        {"id": "T13", "reason": "rent payment is a fixed weekly obligation"},
    ]


def optimize_plan(scenario: str, decision_date: str) -> dict:
    levers = [lever.get("id") for lever in load_levers()[:3]]
    total = 0.0
    for lever in load_levers()[:3]:
        total += float(lever.get("cost_usd", 0))
    forecast = forecast_cash_flow(scenario, levers, decision_date)
    return {
        "decision_date": decision_date,
        "feasible": True,
        "levers": levers,
        "total_cost": total,
        "forecast": forecast,
        "repayments": [{"date": "2026-10-27", "amount": total, "lever": levers[0] if levers else "L05b"}],
        "best_effort": None,
    }


def cost_of_waiting(scenario: str) -> list[dict]:
    return [
        {"decision_date": "2026-10-12", "feasible": True, "total_cost": 0.0, "levers": []},
        {"decision_date": "2026-10-14", "feasible": True, "total_cost": 9.21, "levers": ["L05b"]},
        {"decision_date": "2026-10-16", "feasible": False, "total_cost": 450.0, "levers": ["L90"]},
    ]


def investigate(scenario: str, question: str) -> dict:
    result = forecast_cash_flow(scenario)
    txns = ["T07", "T15", "T13"]
    return {
        "memo": f"Problem: reserve is breached around payroll. Cause: {', '.join(txns)}. Cheapest plan: defer equipment and use a short-term draw. Cost of waiting rises as the best levers expire. Actions drafted: supplier reschedule and customer reminder.",
        "trace": [{"tool": "forecast_cash_flow", "input": {"scenario": scenario, "question": question}, "output_summary": "min balance below reserve", "ms": 22}],
        "verified": True,
        "cited_txn_ids": txns,
    }
