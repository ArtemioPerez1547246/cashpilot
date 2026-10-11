"""ForeCash API. Thin routes over the engine, agent, action queue and monitor."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import monitor
from .actions import clear as clear_actions, get_action, list_actions, set_status
from .agent import agent as agent_mod, investigate
from .devrev_board import store as board
from .engine import scenarios as S

@asynccontextmanager
async def lifespan(_app):
    board.clear_applied()      # the live scenario starts fresh on every restart, so the "already applied" flags must too
    clear_actions()            # drafts belonged to the previous live state
    if os.getenv("DISABLE_MONITOR_TIMER") != "1":
        monitor.start_timer()
    yield


app = FastAPI(title="ForeCash API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(KeyError)
async def _key_error(_, exc):
    return JSONResponse(status_code=404, content={"error": "not_found", "detail": str(exc).strip("'")})


@app.exception_handler(ValueError)
async def _value_error(_, exc):
    return JSONResponse(status_code=400, content={"error": "bad_request", "detail": str(exc)})


class SimulateRequest(BaseModel):
    scenario: str = "live"
    lever_ids: list[str] = Field(default_factory=list)
    decision_date: str = S.START
    extra_changes: list[dict] = Field(default_factory=list)


class OptimizeRequest(BaseModel):
    scenario: str = "live"
    decision_date: str = S.START


class InvestigateRequest(BaseModel):
    scenario: str = "live"
    question: str = Field("Will we run short of cash this week? Explain why and what to do.", max_length=300)


class EventRequest(BaseModel):
    type: str = "payment_delayed"
    txn: str
    days: int = Field(0, ge=-30, le=30)


@app.get("/api/health")
def health():
    return {"ok": True, "model_provider": agent_mod.provider(), "version": app.version}


@app.get("/api/scenarios")
def scenarios():
    return [{"id": k, "label": v["label"], "changes": v["changes"]} for k, v in S.SCENARIOS.items()]


@app.get("/api/levers")
def levers():
    return [lv.model_dump() for lv in S.LEVERS]


@app.get("/api/transactions")
def transactions(scenario: str = "live"):
    return [t.model_dump() for t in S.transactions(scenario)]


@app.get("/api/overview")
def overview(scenario: str = "live"):
    f = S.forecast(scenario)
    txns = sorted(S.transactions(scenario), key=lambda t: (t.date, t.id))
    return {"settings": S.settings(), "scenario": scenario, "forecast": f.model_dump(),
            "upcoming_obligations": [t.model_dump() for t in txns if t.direction == "out"]}


@app.get("/api/forecast")
def forecast(scenario: str = "live"):
    return S.forecast(scenario).model_dump()


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    return S.forecast(req.scenario, req.lever_ids, req.decision_date, req.extra_changes).model_dump()


@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    return S.optimize(req.scenario, req.decision_date).model_dump()


@app.get("/api/cost-of-waiting")
def cost_of_waiting(scenario: str = "live"):
    return [p.model_dump() for p in S.cost_of_waiting(scenario)]


@app.get("/api/drivers")
def drivers(scenario: str = "live"):
    return S.drivers(scenario).model_dump()


@app.post("/api/investigate")
def investigate_route(req: InvestigateRequest):
    return investigate(req.scenario, req.question)


@app.post("/api/events")
def events(req: EventRequest):
    alert = monitor.handle_event(req.type, req.txn, req.days)
    return {"alert": alert, "forecast": S.forecast("live").model_dump()}


@app.get("/api/alerts")
def alerts():
    return monitor.get_alerts()


@app.get("/api/actions")
def actions():
    return [a.model_dump() for a in list_actions()]


def _decide(action_id, status):
    a = set_status(action_id, status)
    if a is None:
        raise HTTPException(404, detail=f"action {action_id} not found")
    return a.model_dump()


@app.post("/api/actions/{action_id}/approve")
def approve(action_id: str):
    return _decide(action_id, "approved")


@app.post("/api/actions/{action_id}/reject")
def reject(action_id: str):
    return _decide(action_id, "rejected")


@app.post("/api/demo/reset")
def demo_reset():
    """Back to a clean normal week: no live events, no alerts, empty action queue."""
    S.reset_live()
    monitor.reset()
    clear_actions()
    board.clear_applied()  # website updates can be re-applied in the next rehearsal
    return {"ok": True}


# ---------- DevRev follow-up board (team-authored synthetic transcripts; separate database) ----------
@app.get("/api/devrev/follow-ups")
def devrev_follow_ups(account: str = "", status: str = "", limit: int = 100, offset: int = 0):
    return board.list_follow_ups(account, status, limit, offset)


@app.post("/api/devrev/follow-ups/{follow_up_id}/status")
def devrev_set_status(follow_up_id: str, status: str):
    f = board.set_status(follow_up_id, status)
    if f is None:
        raise HTTPException(404, detail=f"follow-up {follow_up_id} not found")
    return f


class PaymentUpdate(BaseModel):
    txn: str
    new_date: str
    said_by: str
    channel: str = "in person"
    quote: str = ""
    customer: str = ""


@app.post("/api/devrev/payment-update/preview")
def payment_update_preview(req: PaymentUpdate):
    from .devrev_board import payment_update
    return payment_update.preview(req.txn, req.new_date, req.said_by, req.channel, req.quote, req.customer)


@app.post("/api/devrev/payment-update/apply")
def payment_update_apply(req: PaymentUpdate):
    from .devrev_board import payment_update
    return payment_update.apply(req.txn, req.new_date, req.said_by, req.channel, req.quote, req.customer)
