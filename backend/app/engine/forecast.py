import datetime as dt
from .models import Day, ForecastResult

def forecast(txns, opening_cash, start, horizon, reserve):
    """Walk the horizon day by day. closing = opening + inflows - outflows."""
    d0, bal, days = dt.date.fromisoformat(start), opening_cash, []
    for n in range(horizon):
        day = (d0 + dt.timedelta(days=n)).isoformat()
        today = [t for t in txns if t.date == day]
        i = sum(t.amount for t in today if t.direction == "in")
        o = sum(t.amount for t in today if t.direction == "out")
        days.append(Day(date=day, opening=bal, inflows=i, outflows=o,
                        closing=bal + i - o, txn_ids=[t.id for t in today]))
        bal = bal + i - o
    low = min(days, key=lambda d: d.closing)
    below = next((d.date for d in days if d.closing < reserve), None)
    neg = next((d.date for d in days if d.closing < 0), None)
    return ForecastResult(days=days, ending_cash=days[-1].closing,
                          min_balance=low.closing, min_date=low.date,
                          first_below_reserve=below, first_negative=neg,
                          shortfall_vs_reserve=max(0, reserve - low.closing),
                          total_inflows=sum(d.inflows for d in days),
                          total_outflows=sum(d.outflows for d in days),
                          net_change=days[-1].closing - opening_cash)
