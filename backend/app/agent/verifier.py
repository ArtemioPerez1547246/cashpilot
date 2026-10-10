from __future__ import annotations

from ..engine.forecast import load_transactions, forecast_cash_flow, drivers, optimize_plan, cost_of_waiting


def get_transactions(date_range=None, category=None, txn_id=None):
    txns = load_transactions()
    if txn_id:
        txns = [txn for txn in txns if txn.get("id") == txn_id]
    if category:
        txns = [txn for txn in txns if txn.get("category") == category]
    if date_range:
        start, end = date_range
        txns = [txn for txn in txns if start <= txn.get("date") <= end]
    return {"transactions": txns}


def forecast_cash_flow_tool(scenario, lever_ids=None, decision_date=None):
    return forecast_cash_flow(scenario, lever_ids or [], decision_date)


def find_drivers(scenario):
    return {"drivers": drivers(scenario)}


def optimize_plan_tool(scenario, decision_date):
    return optimize_plan(scenario, decision_date)


def cost_of_waiting_tool(scenario):
    return {"results": cost_of_waiting(scenario)}


def draft_action(scenario, lever, txn_id):
    return {
        "id": "A1",
        "idempotency_key": f"{scenario}:{lever}:{txn_id}",
        "lever_id": lever,
        "type": "email_draft",
        "to": "supplier",
        "subject": "Cash support request",
        "body": "This is a draft action; it is not yet approved.",
        "source_txn_ids": [txn_id],
        "status": "pending",
    }
