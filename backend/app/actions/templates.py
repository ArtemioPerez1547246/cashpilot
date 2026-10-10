"""Message drafts for each kind of lever. Plain templates filled from the data, so every
amount and date in a draft comes from the dataset or the lever file, never from the model."""
from ..engine import scenarios as S
from .store import draft_action

_RECIPIENT = {"T10": "Fruit supplier", "T16": "Dairy supplier", "T14": "Freezer vendor",
              "T13": "Landlord", "T11": "Ad agency", "T08": "Ridgeline Corp"}


def _money(x):
    return f"${x:,.2f}".replace(".00", "")


def draft_for_lever(lever_id, scenario="live"):
    lv = S.LEVERS_BY_ID[lever_id]
    by_id = {t.id: t for t in S.transactions(scenario)}
    targets = [e.txn for e in lv.effects if e.txn]
    t = by_id.get(targets[0]) if targets else None
    shift = next((e.days for e in lv.effects if e.op == "shift"), 0)
    add = next((e.amount for e in lv.effects if e.op == "add"), 0)
    biz = S.BUSINESS["name"]

    if lv.action_type == "supplier_reschedule" and t is not None:
        recipient = _RECIPIENT.get(t.id, "Supplier")
        subject = f"Request to move payment for {t.description}"
        body = (f"Hi, this is {biz}. Could we move the {_money(t.amount)} payment due {t.date} "
                f"by {shift} days? Everything else stays the same. Thank you. [{t.id}]")
    elif lv.action_type in ("credit_draw", "advance_request"):
        recipient = "Our bank / financing provider"
        subject = f"Request: {lv.name}"
        body = (f"Hi, {biz} would like to request {lv.name.lower()} for {_money(add)}. "
                f"Quoted cost: {_money(lv.cost_usd)} ({lv.cost_basis}).")
    else:
        recipient = "Owner (internal)"
        subject = lv.name
        body = f"Internal note: {lv.name}. Estimated cost {_money(lv.cost_usd)} ({lv.cost_basis})."

    return draft_action(lever_id, lv.action_type or "note", recipient, subject, body,
                        [t.id] if t is not None else [], scenario)
