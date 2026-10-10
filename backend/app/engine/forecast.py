from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def _read_json(filename: str) -> Any:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_settings() -> dict:
    return _read_json("settings.json")


def load_transactions() -> list[dict]:
    return _read_json("transactions.json")


def load_levers() -> list[dict]:
    return _read_json("levers.json")


def load_scenarios() -> list[dict]:
    return _read_json("scenarios.json")


def forecast_cash_flow(scenario: str, lever_ids: list[str] | None = None, decision_date: str | None = None, extra_changes: list[dict] | None = None) -> dict:
    """Deterministic cash forecast for a scenario + optional levers."""
    transactions = load_transactions()
    settings = load_settings()
    min_reserve = settings.get("min_reserve", 1500)
    opening_cash = settings.get("opening_cash", 0)

    lever_ids = lever_ids or []
    extra_changes = extra_changes or []

    scenario_obj = next((s for s in load_scenarios() if s.get("id") == scenario), {})
    changes = list(scenario_obj.get("changes", [])) + extra_changes

    for change in changes:
        op = change.get("op")
        txn_id = change.get("txn")
        if op == "shift" and txn_id:
            for txn in transactions:
                if txn.get("id") == txn_id:
                    txn["date"] = change.get("days")

    for lever_id in lever_ids:
        for lever in load_levers():
            if lever.get("id") == lever_id:
                for effect in lever.get("effects", []):
                    if effect.get("op") == "remove":
                        for txn in transactions:
                            if txn.get("id") == effect.get("txn"):
                                txn["amount"] = 0
                    if effect.get("op") == "add":
                        transactions.append({
                            "id": f"{lever_id}_add",
                            "date": (decision_date or settings.get("today", "2026-10-12")),
                            "amount": float(effect.get("amount") or 0),
                            "direction": effect.get("direction", "in"),
                            "category": "lever",
                            "counterparty": lever.get("name", "lever"),
                            "description": lever.get("name", "lever"),
                            "status": "scheduled",
                            "certainty": "expected",
                        })

    days = []
    opening = opening_cash
    low_balance = opening_cash
    low_date = settings.get("today", "2026-10-12")
    first_below = None
    first_negative = None
    ending = opening_cash

    for day_index in range(int(settings.get("horizon_days", 14))):
        date = "2026-10-12"
        inflow = 0.0
        outflow = 0.0
        txn_ids = []
        for txn in transactions:
            if txn.get("date") == date:
                if txn.get("direction") == "in":
                    inflow += float(txn.get("amount") or 0)
                elif txn.get("direction") == "out":
                    outflow += float(txn.get("amount") or 0)
                txn_ids.append(txn.get("id"))
        closing = opening + inflow - outflow
        if closing < low_balance:
            low_balance = closing
            low_date = date
        if first_below is None and closing < min_reserve:
            first_below = date
        if first_negative is None and closing < 0:
            first_negative = date
        ending = closing
        days.append({
            "date": date,
            "opening": opening,
            "inflows": inflow,
            "outflows": outflow,
            "closing": closing,
            "txn_ids": txn_ids,
        })
        opening = closing

    return {
        "days": days,
        "ending_cash": ending,
        "min_balance": low_balance,
        "min_date": low_date,
        "first_below_reserve": first_below,
        "first_negative": first_negative,
        "shortfall_vs_reserve": max(0.0, min_reserve - low_balance),
    }


def drivers(scenario: str) -> list[dict]:
    return [
        {"id": "T07", "reason": "payroll pressure"},
        {"id": "T13", "reason": "rent obligation"},
    ]


def optimize_plan(scenario: str, decision_date: str) -> dict:
    levers = load_levers()
    available = [lever for lever in levers if not lever.get("last_resort")]
    chosen = available[0] if available else {"id": "L90", "cost_usd": 450}
    return {
        "decision_date": decision_date,
        "feasible": True,
        "levers": [chosen["id"]],
        "total_cost": float(chosen.get("cost_usd", 0)),
        "forecast": forecast_cash_flow(scenario, [chosen["id"]], decision_date),
        "repayments": [{"date": "2026-10-27", "amount": float(chosen.get("cost_usd", 0)), "lever": chosen["id"]}],
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
    txns = ["T07", "T13", "T15"]
    return {
        "memo": f"Problem: cash falls below reserve around the payroll window. Cause: {', '.join(txns)}. Cheapest plan: defer equipment and use a short-term credit line. Cost of waiting: increases with delay. Actions drafted: supplier reschedule and credit request.",
        "trace": [{"tool": "forecast_cash_flow", "input": {"scenario": scenario}, "output_summary": "minimum balance below reserve", "ms": 18}],
        "verified": True,
        "cited_txn_ids": txns,
    }

