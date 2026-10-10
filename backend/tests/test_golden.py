from app.engine.loader import load_dataset
from app.engine.forecast import forecast

RAW, TXNS = load_dataset()
B = RAW["business"]
RESERVE = 1500
OUTSIDE = "2026-10-21"  # after the 7-day window (Oct 12-18)

def run(txns):
    return forecast(txns, B["start_cash"], B["start_date"], B["horizon_days"], RESERVE)

def move(txns, tx_id, new_date):
    return [t.model_copy(update={"date": new_date}) if t.id == tx_id else t for t in txns]

def find(category):
    return next(t.id for t in TXNS if t.category == category)

def test_normal_operations():
    r = run(TXNS)
    assert (r.ending_cash, r.min_balance) == (2000, 1800)
    assert r.first_negative is None and r.shortfall_vs_reserve == 0

def test_late_invoice():
    r = run(move(TXNS, find("catering_invoice"), OUTSIDE))
    assert (r.ending_cash, r.min_balance, r.min_date) == (-2000, -2200, "2026-10-16")
    assert r.first_negative == "2026-10-16"
    assert r.shortfall_vs_reserve == 3700

def test_oven_deferral_alone_is_fragile():
    late = move(TXNS, find("catering_invoice"), OUTSIDE)
    r = run(move(late, find("equipment"), OUTSIDE))
    assert (r.ending_cash, r.min_balance) == (500, 300)
    assert r.first_negative is None
    assert r.shortfall_vs_reserve == 1200   # still below the $1,500 reserve

def test_daily_balances_late_invoice():
    r = run(move(TXNS, find("catering_invoice"), OUTSIDE))
    assert [d.closing for d in r.days] == [8950, 7900, 8300, 7100, -2200, -400, -2000]
