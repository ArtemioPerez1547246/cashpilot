from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine.forecast import forecast_cash_flow, optimize_plan, cost_of_waiting, investigate, load_transactions, load_levers, load_scenarios
from .engine.models import ForecastResult, Plan, CostOfWaitingEntry
from .actions.store import actions_store, alerts_store, create_action, approve_action, reject_action
from .monitor import handle_event, get_alerts

app = FastAPI(title="CashPilot", version="0.1.0")


class ForecastRequest(BaseModel):
    scenario: str = Field(..., description="Scenario identifier")
    decision_date: str | None = None


class OptimizeRequest(BaseModel):
    scenario: str = Field(...)
    decision_date: str = Field(...)


class SimulateRequest(BaseModel):
    scenario: str = Field(...)
    lever_ids: list[str] = []
    extra_changes: list[dict] = []


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
def overview(scenario: str = "base"):
    result = forecast_cash_flow(scenario, [])
    settings = load_transactions()
    return {
        "business": "Paletería demo",
        "today": "2026-10-12",
        "setting": settings,
        "forecast": result,
        "upcoming_obligations": result["days"],
    }


@app.get("/api/forecast")
def forecast(scenario: str, decision_date: str | None = None):
    return forecast_cash_flow(scenario, [], decision_date or "2026-10-12")


@app.post("/api/simulate")
def simulate(payload: SimulateRequest):
    return forecast_cash_flow(payload.scenario, payload.lever_ids, payload.extra_changes)


@app.post("/api/optimize")
def optimize(payload: OptimizeRequest):
    return optimize_plan(payload.scenario, payload.decision_date)


@app.get("/api/cost-of-waiting")
def cost_waiting(scenario: str):
    return cost_of_waiting(scenario)


@app.post("/api/investigate")
def investigate_endpoint(payload: InvestigateRequest):
    memo = investigate(payload.scenario, payload.question)
    return memo


@app.post("/api/events")
def events(payload: EventRequest):
    alert = handle_event(payload.type, payload.txn, payload.days)
    return alert


@app.get("/api/alerts")
def alerts():
    return get_alerts()


@app.get("/api/actions")
def actions():
    return {"actions": actions_store}


@app.post("/api/actions/{action_id}/approve")
def approve(action_id: str):
    return approve_action(action_id)


@app.post("/api/actions/{action_id}/reject")
def reject(action_id: str):
    return reject_action(action_id)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return {"error": exc.detail, "detail": exc.detail}
