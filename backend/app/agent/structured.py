"""Structured memo: Strands returns a typed CashMemo (structured_output_model), and every key number
is checked against the engine FIELD BY FIELD, so a right number in the wrong place is caught.

The regex verifier only proves each dollar amount appears somewhere in the tool outputs. This check
proves the lowest balance is the lowest balance, the plan is the optimizer's plan, and each
cost-of-waiting value belongs to its own decision day.
"""
import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field

from ..engine import scenarios as S


class WaitCost(BaseModel):
    decision_date: str = Field(description="YYYY-MM-DD, exactly as returned by cost_of_waiting")
    cost_usd: Optional[float] = Field(description="total cost for that day, or null if there is no safe plan")


class CashMemo(BaseModel):
    """A short cash memo for the business owner. Copy every number from tool outputs; never calculate."""
    problem: str = Field(description="1-2 plain sentences: how low cash goes, on which day, vs the reserve")
    lowest_balance_usd: float = Field(description="min_balance from forecast_cash_flow")
    lowest_balance_date: str = Field(description="min_date from forecast_cash_flow, YYYY-MM-DD")
    cause: str = Field(description="1-2 sentences naming the causes, citing transaction IDs in brackets like [T08]")
    cause_txn_ids: list[str] = Field(description="transaction IDs named as causes, from find_drivers")
    plan: str = Field(description="1-2 sentences describing the cheapest safe plan from optimize_plan")
    plan_lever_ids: list[str] = Field(description="lever IDs in optimize_plan's plan, e.g. L01; empty if none")
    plan_cost_usd: float = Field(description="total_cost from optimize_plan")
    cost_of_waiting: list[WaitCost] = Field(description="one entry per point returned by cost_of_waiting, same order")
    actions_drafted: list[str] = Field(description="action IDs returned by draft_action, e.g. A001")


def _same(a, b):
    return a is None and b is None or (a is not None and b is not None and abs(float(a) - float(b)) < 0.01)


def semantic_check(m, scenario="live"):
    """Compare each field with what the engine says right now. Returns [{field, ok, expected, got}]."""
    f = S.forecast(scenario)
    p = S.optimize(scenario, S.START)
    pts = S.cost_of_waiting(scenario)
    d = S.drivers(scenario)
    causes = {o.txn_id for o in d.outflows} | {x.txn_id for x in d.pushed_inflows}
    must = {x.txn_id for x in d.pushed_inflows[:1]}                  # the biggest late payment must be named
    out = [
        {"field": "lowest_balance_usd", "expected": f.min_balance, "got": m.lowest_balance_usd},
        {"field": "lowest_balance_date", "expected": f.min_date, "got": m.lowest_balance_date},
        {"field": "plan_lever_ids", "expected": sorted(p.levers) if p.feasible else [], "got": sorted(m.plan_lever_ids)},
        {"field": "plan_cost_usd", "expected": p.total_cost if p.feasible else 0.0, "got": m.plan_cost_usd},
        {"field": "cost_of_waiting", "expected": [(x.decision_date, x.total_cost) for x in pts],
         "got": [(w.decision_date, w.cost_usd) for w in m.cost_of_waiting]},
        {"field": "cause_txn_ids", "expected": f"includes {sorted(must)}, only known drivers", "got": sorted(m.cause_txn_ids)},
    ]
    for c in out:
        e, g = c["expected"], c["got"]
        if c["field"] in ("lowest_balance_usd", "plan_cost_usd"):
            c["ok"] = _same(e, g)
        elif c["field"] == "cost_of_waiting":
            c["ok"] = len(e) == len(g) and all(ed == gd and _same(ec, gc) for (ed, ec), (gd, gc) in zip(e, g))
        elif c["field"] == "cause_txn_ids":
            c["ok"] = must <= set(g) and set(g) <= causes
        else:
            c["ok"] = e == g
    return out


def _money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def _day(s):
    d = dt.date.fromisoformat(s[:10])
    return f"{d:%a %b} {d.day}"


def render(m):
    """Memo text for the dashboard. The prose is the model's; the cost-of-waiting line is built from the
    checked fields."""
    wait = "; ".join(f"decide {_day(w.decision_date)}: " + (_money(w.cost_usd) if w.cost_usd is not None
                                                          else "no safe plan") for w in m.cost_of_waiting)
    acts = ", ".join(m.actions_drafted) or "none"
    return (f"## Problem\n{m.problem}\n\n## Cause\n{m.cause}\n\n## Cheapest plan\n{m.plan}\n\n"
            f"## Cost of waiting\n{wait}.\n\n## Actions drafted\n{acts} (waiting for owner approval).")
