from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    id: str
    date: str
    amount: float
    direction: str = Field(..., description="in or out")
    category: str
    counterparty: str | None = None
    description: str
    status: str = "scheduled"
    certainty: str = "committed"


class LeverEffect(BaseModel):
    op: str
    txn: str | None = None
    days: int | None = None
    direction: str | None = None
    amount: float | None = None
    lead_days: int | None = None


class Lever(BaseModel):
    id: str
    name: str
    effects: list[LeverEffect]
    cost_usd: float
    cost_basis: str
    constraint: str
    deadline: str | None = None
    exclusive_group: str | None = None
    last_resort: bool = False
    action_type: str | None = None


class ScenarioChange(BaseModel):
    op: str
    txn: str | None = None
    days: int | None = None


class Scenario(BaseModel):
    id: str
    label: str
    changes: list[ScenarioChange] = []


class DayForecast(BaseModel):
    date: str
    opening: float
    inflows: float
    outflows: float
    closing: float
    txn_ids: list[str]


class ForecastResult(BaseModel):
    days: list[DayForecast]
    ending_cash: float
    min_balance: float
    min_date: str | None = None
    first_below_reserve: str | None = None
    first_negative: str | None = None
    shortfall_vs_reserve: float = 0.0


class Repayment(BaseModel):
    date: str
    amount: float
    lever: str


class Plan(BaseModel):
    decision_date: str
    feasible: bool
    levers: list[str]
    total_cost: float
    forecast: ForecastResult | dict | None = None
    repayments: list[Repayment] = []
    best_effort: str | None = None


class CostOfWaitingEntry(BaseModel):
    decision_date: str
    feasible: bool
    total_cost: float
    levers: list[str]


class Action(BaseModel):
    id: str
    idempotency_key: str
    lever_id: str
    type: str
    to: str
    subject: str = ""
    body: str = ""
    source_txn_ids: list[str] = []
    status: str = "pending"


__all__ = [
    "Transaction",
    "LeverEffect",
    "Lever",
    "ScenarioChange",
    "Scenario",
    "DayForecast",
    "ForecastResult",
    "Repayment",
    "Plan",
    "CostOfWaitingEntry",
    "Action",
]
