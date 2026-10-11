"""The field-by-field check catches what the regex verifier can't: right number, wrong place."""
from app.agent.structured import CashMemo, WaitCost, render, semantic_check

GOOD = dict(problem="Cash falls to -$2,200 on Oct 16.", lowest_balance_usd=-2200, lowest_balance_date="2026-10-16",
            cause="Ridgeline pays late [T08].", cause_txn_ids=["T08", "T15"],
            plan="Defer the freezer and draw $2,000.", plan_lever_ids=["L05B", "L01"], plan_cost_usd=9.21,
            cost_of_waiting=[WaitCost(decision_date="2026-10-12", cost_usd=9.21),
                             WaitCost(decision_date="2026-10-14", cost_usd=124.6),
                             WaitCost(decision_date="2026-10-16", cost_usd=None)],
            actions_drafted=["A001"])


def bad_fields(**changes):
    return {c["field"] for c in semantic_check(CashMemo(**{**GOOD, **changes}), "disruption") if not c["ok"]}


def test_correct_memo_passes_every_field():
    assert bad_fields() == set()


def test_swapped_costs_are_caught():
    swapped = [WaitCost(decision_date="2026-10-12", cost_usd=124.6), WaitCost(decision_date="2026-10-14", cost_usd=9.21),
               WaitCost(decision_date="2026-10-16", cost_usd=None)]
    assert bad_fields(cost_of_waiting=swapped) == {"cost_of_waiting"}


def test_flipped_sign_and_wrong_day_are_caught():
    assert bad_fields(lowest_balance_usd=2200, lowest_balance_date="2026-10-15") == {"lowest_balance_usd", "lowest_balance_date"}


def test_wrong_plan_and_missing_cause_are_caught():
    assert bad_fields(plan_lever_ids=["L90"], plan_cost_usd=450, cause_txn_ids=["T15"]) == {
        "plan_lever_ids", "plan_cost_usd", "cause_txn_ids"}


def test_render_builds_waiting_line_from_checked_fields():
    text = render(CashMemo(**GOOD))
    assert "decide Mon Oct 12: $9.21" in text and "decide Fri Oct 16: no safe plan" in text
