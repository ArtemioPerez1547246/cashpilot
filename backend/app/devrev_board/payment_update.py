"""'A customer told me they'll pay later': one approval updates the evidence, the DevRev follow-up
board, the cash forecast and (if configured) DevRev itself.

All date and money math is done here in code, never by an AI model.
Idempotent: approving the same change twice moves the payment once and creates one follow-up.
"""
import hashlib
import json
import re
from datetime import date

from .. import monitor
from ..engine import scenarios as S
from . import devrev_sync, store

CHANNELS = ("in person", "phone", "email", "text message", "other")


def _incoming(txn_id):
    for t in S.transactions("live"):
        if t.id == txn_id:
            if t.direction != "in":
                raise ValueError(f"{txn_id} is a payment we make, not money we expect to receive")
            return t
    raise KeyError(f"unknown transaction {txn_id}")


def guess_customer(description):
    m = re.match(r"([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*)", description or "")
    return m.group(1) if m else ""


def _summary(f):
    return {"lowest": f.min_balance, "lowest_date": f.min_date, "ending": f.ending_cash}


def _draft(txn_id, new_date, said_by, channel, quote, customer):
    t = _incoming(txn_id)
    try:
        nd = date.fromisoformat(new_date)
    except ValueError:
        raise ValueError("new_date must be YYYY-MM-DD")
    days = (nd - date.fromisoformat(t.date)).days
    if days <= 0:
        raise ValueError(f"The new date must be after the currently expected date ({t.date}).")
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}")
    said_by = (said_by or "").strip()
    if not said_by:
        raise ValueError("Who said it? Enter the person's name.")
    customer = (customer or "").strip() or guess_customer(t.description) or t.description
    inv = re.search(r"INV-\d+", t.description)
    key = f"owner:{txn_id}:{new_date}"
    note = {"type": "owner note of a verbal statement", "txn": txn_id, "customer": customer,
            "said_by": said_by, "channel": channel, "quote": (quote or "").strip()[:300],
            "old_date": t.date, "new_date": new_date, "amount": t.amount}
    sha = hashlib.sha256(json.dumps(note, sort_keys=True).encode()).hexdigest()
    title = f"{customer} to pay {inv.group(0) + ' ' if inv else ''}(${t.amount:,.0f}) on {new_date}"
    details = (f"They promised: {said_by} ({customer}) told the owner {channel} that this payment will "
               f"arrive on {new_date} instead of {t.date} ({days} days later). Recorded by the owner; "
               f"no call transcript exists for this statement.")
    fields = dict(account=customer, title=title, details=details, owner=said_by, due_date=new_date,
                  requested_by="ForeCash owner (website)",
                  sources=[{"ref": f"owner-note:{txn_id}:{new_date}", "sha256": sha,
                            "quote": note["quote"] or f"(verbal, {channel})"}])
    return t, days, key, fields


def preview(txn_id, new_date, said_by, channel="in person", quote="", customer=""):
    if store.is_applied(f"owner:{txn_id}:{new_date}"):
        raise ValueError(f"Already recorded: {txn_id} is already set to {new_date}. Press Reset demo to try again.")
    t, days, key, fields = _draft(txn_id, new_date, said_by, channel, quote, customer)
    before = S.forecast("live")
    after = S.forecast("live", extra_changes=[{"op": "shift", "txn": txn_id, "days": days}])
    existing = store.find_open_match(fields["account"], new_date)
    return {"txn": txn_id, "description": t.description, "amount": t.amount, "old_date": t.date,
            "new_date": new_date, "days_later": days, "before": _summary(before), "after": _summary(after),
            "reserve": S.settings()["min_reserve"], "follow_up": {**fields, "idempotency_key": key},
            "already_recorded": existing["id"] if existing else None,
            "devrev_sync": devrev_sync.configured()}


def apply(txn_id, new_date, said_by, channel="in person", quote="", customer=""):
    if store.is_applied(f"owner:{txn_id}:{new_date}"):  # repeat click: answer before re-checking dates
        return {"follow_up": None, "created": False, "alert": None, "devrev": None,
                "note": "Already recorded; the forecast was not changed again."}
    t, days, key, fields = _draft(txn_id, new_date, said_by, channel, quote, customer)
    if not store.mark_applied(key):  # double click or repeat: never shift the payment twice
        return {"follow_up": store.find_open_match(fields["account"], new_date), "created": False,
                "alert": None, "devrev": None, "note": "Already recorded; the forecast was not changed again."}
    alert = monitor.handle_event("payment_delayed", txn_id, days)
    match = store.find_open_match(fields["account"], new_date)
    if match:  # DevRev already tracks this promise (e.g. found in a call transcript): don't duplicate it
        return {"follow_up": match, "created": False, "alert": alert, "devrev": None,
                "note": f"Payment moved {days} days. DevRev already tracks this promise as {match['id']}."}
    res = store.create(idempotency_key=key, **fields)
    sync = devrev_sync.post_comment(f"[ForeCash] {fields['title']}. {fields['details']}"
                                    + (f' Quote: "{fields["sources"][0]["quote"]}"' if quote else ""))
    return {"follow_up": res["follow_up"], "created": True, "alert": alert, "devrev": sync,
            "note": f"Payment moved {days} days; follow-up {res['follow_up']['id']} created."}
