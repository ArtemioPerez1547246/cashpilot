"""Scenario state shared by the API, the agent tools and the monitor.

Every number still comes from forecast() / optimize() / drivers(). This module only decides
WHICH transactions those functions see: the base plan, a named scenario, or the "live"
scenario that the monitor changes when events arrive.
"""
import datetime as dt
from threading import Lock

from .drivers import drivers as _drivers
from .forecast import forecast as _forecast
from .loader import load_dataset, load_levers
from .optimizer import apply_levers, cost_of_waiting as _cost_of_waiting, optimize as _optimize

RAW, BASE = load_dataset()
LEVERS = load_levers()
LEVERS_BY_ID = {lv.id: lv for lv in LEVERS}
BUSINESS = RAW["business"]
OPENING, START, HORIZON = BUSINESS["start_cash"], BUSINESS["start_date"], BUSINESS["horizon_days"]
RESERVE = 1500

SCENARIOS = {
    "normal": {"label": "Normal week", "changes": []},
    "disruption": {"label": "Ridgeline pays 6 days late",
                   "changes": [{"op": "set_date", "txn": "T08", "date": "2026-10-21"}]},
    "live": {"label": "Live (changed by events)", "changes": []},
}
_lock = Lock()


def settings():
    return {"business": BUSINESS["name"], "today": START, "horizon_days": HORIZON,
            "min_reserve": RESERVE, "opening_cash": OPENING}


def _apply(txns, change):
    tid = change.get("txn")
    if tid not in {t.id for t in txns}:
        raise KeyError(f"unknown transaction {tid}")
    out = []
    for t in txns:
        if t.id != tid:
            out.append(t)
        elif change["op"] == "shift":
            new = (dt.date.fromisoformat(t.date) + dt.timedelta(days=int(change["days"]))).isoformat()
            out.append(t.model_copy(update={"date": new}))
        elif change["op"] == "set_date":
            out.append(t.model_copy(update={"date": change["date"]}))
        elif change["op"] == "remove":
            continue
        else:
            raise ValueError(f"unknown change op {change['op']}")
    return out


def transactions(scenario="normal", extra_changes=()):
    if scenario not in SCENARIOS:
        raise KeyError(f"unknown scenario {scenario}; use one of {sorted(SCENARIOS)}")
    txns = list(BASE)
    with _lock:
        changes = list(SCENARIOS[scenario]["changes"])
    for c in list(changes) + list(extra_changes):
        txns = _apply(txns, c)
    return txns


def _levers(ids):
    missing = [i for i in ids if i not in LEVERS_BY_ID]
    if missing:
        raise KeyError(f"unknown levers {missing}")
    return [LEVERS_BY_ID[i] for i in ids]


def forecast(scenario="normal", lever_ids=(), decision_date=START, extra_changes=()):
    txns = transactions(scenario, extra_changes)
    if lever_ids:
        txns = apply_levers(txns, _levers(lever_ids), decision_date)
    return _forecast(txns, OPENING, START, HORIZON, RESERVE)


def drivers(scenario="normal"):
    return _drivers(BASE, transactions(scenario), OPENING, START, HORIZON, RESERVE)


def optimize(scenario="normal", decision_date=START):
    return _optimize(transactions(scenario), LEVERS, OPENING, START, HORIZON, RESERVE, decision_date)


def cost_of_waiting(scenario="normal", offsets=(0, 2, 4)):
    return _cost_of_waiting(transactions(scenario), LEVERS, OPENING, START, HORIZON, RESERVE, offsets)


def add_live_change(change):
    _apply(transactions("live"), change)  # validate before storing
    with _lock:
        SCENARIOS["live"]["changes"].append(change)


def reset_live():
    with _lock:
        SCENARIOS["live"]["changes"].clear()
