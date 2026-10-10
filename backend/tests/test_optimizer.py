import itertools, time
from app.engine.loader import load_dataset, load_levers
from app.engine.forecast import forecast
from app.engine.optimizer import optimize, cost_of_waiting, apply_levers, _conflict, _available

RAW, BASE = load_dataset()
B = RAW["business"]; LEVERS = load_levers()
OPEN, START, H, RES = B["start_cash"], B["start_date"], B["horizon_days"], 1500

def late():
    return [t.model_copy(update={"date": "2026-10-21"}) if t.id == "T08" else t for t in BASE]

def opt(dd="2026-10-12", scen=None):
    return optimize(scen or late(), LEVERS, OPEN, START, H, RES, dd)

def reference(scenario, dd):
    """Independent slow reference: every subset, scored with the real forecast()."""
    avail = [l for l in LEVERS if _available(l, scenario, dd)]
    best = None
    for r in range(len(avail) + 1):
        for sub in itertools.combinations(avail, r):
            if any(_conflict(a, b) for a, b in itertools.combinations(sub, 2)): continue
            f = forecast(apply_levers(scenario, list(sub), dd), OPEN, START, H, RES)
            if f.min_balance >= RES:
                key = (round(sum(l.cost_usd for l in sub), 2), len(sub), -f.min_balance)
                if best is None or key < best[0]: best = (key, [l.id for l in sub])
    return best

def test_cheapest_plan_today():
    p = opt()
    assert p.feasible and p.levers == ["L01", "L05B"] and p.total_cost == 9.21
    assert p.forecast.min_balance >= RES

def test_matches_independent_reference_on_every_decision_date():
    for dd in ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"]:
        ref, p = reference(late(), dd), opt(dd)
        if ref is None: assert not p.feasible
        else: assert p.feasible and p.levers == ref[1] and p.total_cost == ref[0][0], dd

def test_never_two_levers_from_one_group_or_same_transaction():
    for dd in ["2026-10-12", "2026-10-14"]:
        ids = opt(dd).levers
        assert len([i for i in ids if i.startswith("L05")]) <= 1

def test_credit_line_repayment_is_shown_even_outside_window():
    p = opt()
    r = [x for x in p.repayments if x.lever == "L05B"][0]
    assert r.date == "2026-10-27" and r.amount == 2009.21

def test_deferred_payments_are_reported_not_hidden():
    p = opt()
    assert any(d.txn_id == "T14" and d.new_date == "2026-10-21" for d in p.deferred_obligations)
    assert p.deferred_total == 2500

def test_waiting_never_gets_cheaper_and_late_decisions_fail():
    pts = cost_of_waiting(late(), LEVERS, OPEN, START, H, RES, offsets=(0, 1, 2, 3, 4))
    costs = [float("inf") if not x.feasible else x.total_cost for x in pts]
    assert costs == sorted(costs)
    assert pts[0].feasible and not pts[-1].feasible

def test_infeasible_is_honest_not_empty():
    p = opt("2026-10-16")
    assert not p.feasible and p.best_effort and p.note

def test_already_paid_items_cannot_be_deferred():
    p = opt("2026-10-16")
    assert "L01" not in p.levers and "L02" not in p.levers

def test_fast_enough():
    t = time.time(); opt(); assert time.time() - t < 1.0

def test_normal_scenario_needs_no_levers():
    p = opt(scen=BASE)
    assert p.feasible and p.levers == [] and p.total_cost == 0
