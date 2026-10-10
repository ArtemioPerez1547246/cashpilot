import datetime as dt
from .forecast import forecast
from .models import (Txn, Plan, PlanRepayment, Deferred, WaitPoint)

def add_days(date, n):
    return (dt.date.fromisoformat(date) + dt.timedelta(days=n)).isoformat()

def apply_levers(txns, levers, decision_date):
    """Ground truth: apply levers to a copy of the transactions. Slow but obviously correct."""
    out = {t.id: t.model_copy() for t in txns}
    removed, extra = set(), []
    for lv in levers:
        for e in lv.effects:
            if e.op in ("shift", "remove") and e.txn not in out:
                raise KeyError(f"lever {lv.id} targets unknown transaction {e.txn}")
            if e.op == "shift":
                out[e.txn] = out[e.txn].model_copy(update={"date": add_days(out[e.txn].date, e.days)})
            elif e.op == "remove":
                removed.add(e.txn)
            elif e.op == "add":
                extra.append(Txn(id=f"{lv.id}-in", date=add_days(decision_date, e.lead_days), amount=e.amount,
                                 direction=e.direction, category="lever", description=lv.name, status="proposed"))
        for r in lv.repayments:
            extra.append(Txn(id=f"{lv.id}-repay", date=add_days(decision_date, r.lead_days), amount=r.amount,
                             direction="out", category="repayment", description=f"Repay: {lv.name}", status="proposed"))
    return [t for i, t in out.items() if i not in removed] + extra

def _targets(lv):
    return {e.txn for e in lv.effects if e.txn}

def _available(lv, scenario, decision_date):
    if lv.deadline is not None and lv.deadline < decision_date:
        return False
    by = {t.id: t for t in scenario}
    for tid in _targets(lv):          # cannot defer something already paid
        if tid not in by or by[tid].date < decision_date:
            return False
    return True

def _conflict(a, b):
    return (a.exclusive_group is not None and a.exclusive_group == b.exclusive_group) or bool(_targets(a) & _targets(b))

def _net(txns, start, horizon):
    idx = {add_days(start, n): n for n in range(horizon)}
    v = [0.0] * horizon
    for t in txns:
        if t.date in idx:
            v[idx[t.date]] += t.amount if t.direction == "in" else -t.amount
    return v

def optimize(scenario, levers, opening_cash, start, horizon, reserve, decision_date):
    """Cheapest set of levers keeping cash >= reserve on every day. Never fakes a solution."""
    avail = [lv for lv in levers if _available(lv, scenario, decision_date)]
    base = _net(scenario, start, horizon)
    deltas = [[a - b for a, b in zip(_net(apply_levers(scenario, [lv], decision_date), start, horizon), base)] for lv in avail]
    n = len(avail)
    best = {"feasible": None, "effort": None}

    def evaluate(chosen, net, cost):
        bal, low = opening_cash, float("inf")
        for x in net:
            bal += x; low = min(low, bal)
        key_f = (round(cost, 2), len(chosen), -low)
        key_e = (-low, round(cost, 2), len(chosen))
        if low >= reserve and (best["feasible"] is None or key_f < best["feasible"][0]):
            best["feasible"] = (key_f, list(chosen))
        if best["effort"] is None or key_e < best["effort"][0]:
            best["effort"] = (key_e, list(chosen))

    def rec(i, chosen, net, cost):
        if i == n:
            evaluate(chosen, net, cost); return
        rec(i + 1, chosen, net, cost)
        if all(not _conflict(avail[i], avail[j]) for j in chosen):
            rec(i + 1, chosen + [i], [a + b for a, b in zip(net, deltas[i])], cost + avail[i].cost_usd)
    rec(0, [], base, 0.0)

    feasible = best["feasible"] is not None
    picked = [avail[i] for i in (best["feasible"] or best["effort"])[1]]
    fc = forecast(apply_levers(scenario, picked, decision_date), opening_cash, start, horizon, reserve)
    end = add_days(start, horizon - 1)
    by = {t.id: t for t in scenario}
    deferred = [Deferred(txn_id=e.txn, lever=lv.id, original_date=by[e.txn].date,
                         new_date=add_days(by[e.txn].date, e.days), amount=by[e.txn].amount)
                for lv in picked for e in lv.effects
                if e.op == "shift" and add_days(by[e.txn].date, e.days) > end]
    repays = [PlanRepayment(date=add_days(decision_date, r.lead_days), amount=r.amount, lever=lv.id)
              for lv in picked for r in lv.repayments]
    note = "" if feasible else "No combination keeps cash at or above the reserve every day. Showing the best attempt."
    return Plan(decision_date=decision_date, feasible=feasible, best_effort=not feasible,
                levers=[lv.id for lv in picked], total_cost=round(sum(lv.cost_usd for lv in picked), 2),
                forecast=fc, repayments=repays, deferred_obligations=deferred,
                deferred_total=sum(d.amount for d in deferred), note=note)

def cost_of_waiting(scenario, levers, opening_cash, start, horizon, reserve, offsets=(0, 2, 4)):
    out = []
    for off in offsets:
        dd = add_days(start, off)
        p = optimize(scenario, levers, opening_cash, start, horizon, reserve, dd)
        out.append(WaitPoint(decision_date=dd, feasible=p.feasible, total_cost=p.total_cost if p.feasible else None,
                             levers=p.levers, min_balance=p.forecast.min_balance))
    return out
