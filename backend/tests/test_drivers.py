from app.engine.loader import load_dataset
from app.engine.drivers import drivers

RAW, BASE = load_dataset()
B = RAW["business"]
OUTSIDE = "2026-10-21"

def move(txns, tx_id, new_date):
    return [t.model_copy(update={"date": new_date}) if t.id == tx_id else t for t in txns]

def run(scenario):
    return drivers(BASE, scenario, B["start_cash"], B["start_date"], B["horizon_days"], 1500)

def late():
    return move(BASE, "T08", OUTSIDE)

def test_pushed_inflow_is_identified_with_impact():
    r = run(late())
    assert [p.txn_id for p in r.pushed_inflows] == ["T08"]
    assert r.pushed_inflows[0].impact_on_min_balance == 4000
    assert r.pushed_inflows[0].planned_date == "2026-10-15"

def test_payroll_is_the_largest_outflow_on_the_dip():
    r = run(late())
    assert r.min_date == "2026-10-16"
    assert r.outflows[0].txn_id == "T15" and r.outflows[0].amount == 8400
    assert r.total_outflows_through_min_date == 16900

def test_outflows_sorted_largest_first_and_stop_at_min_date():
    r = run(late())
    amounts = [d.amount for d in r.outflows]
    assert amounts == sorted(amounts, reverse=True)
    assert all(d.date <= r.min_date for d in r.outflows)
    assert "T13" not in [d.txn_id for d in r.outflows]   # rent is after Oct 16

def test_normal_scenario_has_no_pushed_inflows():
    assert run(BASE).pushed_inflows == []

def test_discretionary_flag_survives_loading():
    r = run(late())
    assert next(d for d in r.outflows if d.txn_id == "T14").flexibility == "discretionary"
