from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.engine.forecast import (
    cost_of_waiting,
    forecast_cash_flow,
    investigate,
    load_transactions,
    optimize_plan,
)

app = FastAPI(title="CashPilot", version="0.1.0")


class SimulateRequest(BaseModel):
    scenario: str = Field(...)
    lever_ids: list[str] = Field(default_factory=list)
    extra_changes: list[dict] = Field(default_factory=list)


class OptimizeRequest(BaseModel):
    scenario: str = Field(...)
    decision_date: str = Field(...)


class InvestigateRequest(BaseModel):
    scenario: str = Field(...)
    question: str = Field(...)


class EventRequest(BaseModel):
    type: str = Field(...)
    txn: str | None = None
    days: int | None = None


@app.get("/api/health")
def health():
    return {"ok": True, "model_provider": "stub", "version": "0.1.0"}


@app.get("/api/overview")
def overview(scenario: str = "A_normal"):
    return {
        "business": "Paletería demo",
        "today": "2026-10-12",
        "settings": {"start_date": "2026-10-12", "horizon_days": 14, "min_reserve": 1500},
        "transactions": load_transactions(),
        "forecast": forecast_cash_flow(scenario),
    }


@app.get("/api/forecast")
def forecast(scenario: str = "A_normal", decision_date: str | None = None):
    return forecast_cash_flow(scenario, [], decision_date or "2026-10-12")


@app.post("/api/simulate")
def simulate(payload: SimulateRequest):
    return forecast_cash_flow(payload.scenario, payload.lever_ids, extra_changes=payload.extra_changes)


@app.post("/api/optimize")
def optimize(payload: OptimizeRequest):
    return optimize_plan(payload.scenario, payload.decision_date)


@app.get("/api/cost-of-waiting")
def cost_waiting(scenario: str = "A_normal"):
    return cost_of_waiting(scenario)


@app.post("/api/investigate")
def investigate_endpoint(payload: InvestigateRequest):
    return investigate(payload.scenario, payload.question)


@app.post("/api/events")
def events(payload: EventRequest):
    return {"alert_id": f"alert-{payload.type}-{payload.txn or 'none'}", "type": payload.type, "status": "created"}


@app.get("/api/alerts")
def alerts():
    return {"alerts": []}


@app.get("/api/actions")
def actions():
    return {"actions": []}


@app.post("/api/actions/{action_id}/approve")
def approve(action_id: str):
    return {"id": action_id, "status": "approved"}


@app.post("/api/actions/{action_id}/reject")
def reject(action_id: str):
    return {"id": action_id, "status": "rejected"}


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return {"error": exc.detail, "detail": exc.detail}
