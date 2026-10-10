from .forecast import forecast
from .models import Driver, PushedInflow, DriversResult

def drivers(base, scenario, opening_cash, start, horizon, reserve):
    """Why is cash short? base = the original plan, scenario = what is happening now."""
    cur = forecast(scenario, opening_cash, start, horizon, reserve)

    # 1. Every outflow from the start through the lowest-balance day, largest first.
    outs = sorted(
        (Driver(txn_id=t.id, date=t.date, amount=t.amount, category=t.category,
                description=t.description, flexibility=t.flexibility)
         for t in scenario
         if t.direction == "out" and start <= t.date <= cur.min_date),
        key=lambda d: -d.amount)

    # 2. Inflows that arrive later than planned, with the counterfactual impact:
    #    "if this had arrived on time, how much higher would the lowest balance be?"
    base_by_id = {t.id: t for t in base}
    pushed = []
    for t in scenario:
        b = base_by_id.get(t.id)
        if b and t.direction == "in" and t.date > b.date:
            restored = [b if x.id == t.id else x for x in scenario]
            gain = forecast(restored, opening_cash, start, horizon, reserve).min_balance - cur.min_balance
            pushed.append(PushedInflow(txn_id=t.id, description=t.description, amount=t.amount,
                                       planned_date=b.date, actual_date=t.date,
                                       impact_on_min_balance=gain, note=t.note))
    pushed.sort(key=lambda p: -p.impact_on_min_balance)

    return DriversResult(min_date=cur.min_date, min_balance=cur.min_balance,
                         total_outflows_through_min_date=sum(d.amount for d in outs),
                         outflows=outs, pushed_inflows=pushed)
