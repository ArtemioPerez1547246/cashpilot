"""Strands tools. Each one calls the deterministic engine and returns JSON.

Every call is recorded in a per-request trace (tool, input, short output summary, ms) so the
dashboard can show exactly which tools the agent used. The full outputs are also kept so the
verifier can check every dollar figure in the memo against them.
"""
import contextvars
import time

from strands import tool

from ..actions import draft_for_lever
from ..engine import scenarios as S

_trace = contextvars.ContextVar("trace", default=None)


def start_trace():
    _trace.set({"calls": [], "outputs": []})


def get_trace():
    return _trace.get() or {"calls": [], "outputs": []}


def _record(name, args, out, t0, summary):
    tr = _trace.get()
    if tr is not None:
        tr["calls"].append({"tool": name, "input": args, "output_summary": summary,
                            "ms": round((time.time() - t0) * 1000)})
        tr["outputs"].append(out)
    return out


@tool
def get_transactions(scenario: str = "live", category: str = "", txn_id: str = "") -> dict:
    """List the business's transactions for a scenario. Optionally filter by category or one transaction ID."""
    t0 = time.time()
    rows = [t.model_dump() for t in S.transactions(scenario)]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if txn_id:
        rows = [r for r in rows if r["id"] == txn_id]
    return _record("get_transactions", {"scenario": scenario, "category": category, "txn_id": txn_id},
                   {"transactions": rows}, t0, f"{len(rows)} transactions")


@tool
def forecast_cash_flow(scenario: str = "live", lever_ids: list[str] | None = None,
                       decision_date: str = "2026-10-12") -> dict:
    """Day-by-day cash forecast: closing balance each day, the minimum balance and its date,
    the first day below the reserve, and the shortfall versus the reserve."""
    t0 = time.time()
    f = S.forecast(scenario, lever_ids or [], decision_date).model_dump()
    return _record("forecast_cash_flow", {"scenario": scenario, "lever_ids": lever_ids or [],
                                          "decision_date": decision_date}, f, t0,
                   f"min ${f['min_balance']:,.0f} on {f['min_date']}, ending ${f['ending_cash']:,.0f}")


@tool
def find_drivers(scenario: str = "live") -> dict:
    """Explain WHY cash dips: outflows up to the lowest day (largest first) and any inflows that
    arrive later than planned, with how much each late inflow lowers the minimum balance."""
    t0 = time.time()
    d = S.drivers(scenario).model_dump()
    top = d["pushed_inflows"][0]["txn_id"] if d["pushed_inflows"] else (d["outflows"][0]["txn_id"] if d["outflows"] else "-")
    return _record("find_drivers", {"scenario": scenario}, d, t0, f"top driver {top}")


@tool
def optimize_plan(scenario: str = "live", decision_date: str = "2026-10-12") -> dict:
    """Cheapest combination of levers that keeps cash at or above the reserve on EVERY day,
    if decided on decision_date. Reports feasible=false honestly when nothing works."""
    t0 = time.time()
    p = S.optimize(scenario, decision_date).model_dump()
    s = (f"{'+'.join(p['levers'])} for ${p['total_cost']:,.2f}" if p["feasible"] else "no feasible plan")
    return _record("optimize_plan", {"scenario": scenario, "decision_date": decision_date}, p, t0, s)


@tool
def cost_of_waiting(scenario: str = "live") -> dict:
    """What the cheapest safe plan costs if decided today, in 2 days and in 4 days."""
    t0 = time.time()
    pts = [p.model_dump() for p in S.cost_of_waiting(scenario)]
    s = ", ".join(f"{p['decision_date'][5:]}: " + (f"${p['total_cost']:,.2f}" if p["feasible"] else "infeasible") for p in pts)
    return _record("cost_of_waiting", {"scenario": scenario}, {"points": pts}, t0, s)


@tool
def draft_action(lever_id: str, scenario: str = "live") -> dict:
    """Draft the message for one lever (e.g. a supplier reschedule request) into the owner's
    approval queue. Drafting the same lever twice returns the existing draft. Never sends anything."""
    t0 = time.time()
    a, created = draft_for_lever(lever_id, scenario)
    out = {"action": a.model_dump(), "created": created}
    return _record("draft_action", {"lever_id": lever_id, "scenario": scenario}, out, t0,
                   f"{a.id} {'drafted' if created else 'already existed'}")


ALL_TOOLS = [get_transactions, forecast_cash_flow, find_drivers, optimize_plan, cost_of_waiting, draft_action]
