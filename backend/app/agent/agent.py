"""The CashPilot Strands agent.

MODEL_PROVIDER picks the model with one environment variable:
  akamai   -> Akamai hosted inference (OpenAI-compatible): AKAMAI_BASE_URL, AKAMAI_API_KEY, AKAMAI_MODEL
  bedrock  -> Amazon Bedrock: BEDROCK_MODEL, AWS_REGION (+ normal AWS credentials)
  stub     -> no model: the same tools run in a fixed order and a template writes the memo.

The response always says which mode produced the memo ("mode"), so we never present a
template memo as AI output.
"""
import os

from ..engine import scenarios as S
from .prompts import SYSTEM_PROMPT
from .tools import (ALL_TOOLS, cost_of_waiting, draft_action, find_drivers, forecast_cash_flow,
                    get_trace, optimize_plan, start_trace)
from .verifier import verify


def provider():
    return os.getenv("MODEL_PROVIDER", "stub").lower()


def make_model():
    p = provider()
    if p == "akamai":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(client_args={"api_key": os.environ["AKAMAI_API_KEY"],
                                        "base_url": os.getenv("AKAMAI_BASE_URL", "https://ws.akamai-workshops.com/v1")},
                           model_id=os.getenv("AKAMAI_MODEL", "hackathon-chat"))
    if p == "openai":  # any OpenAI-compatible service (OpenAI itself, or another provider's base URL)
        from strands.models.openai import OpenAIModel
        args = {"api_key": os.environ["OPENAI_API_KEY"]}
        if os.getenv("OPENAI_BASE_URL"):
            args["base_url"] = os.environ["OPENAI_BASE_URL"]
        return OpenAIModel(client_args=args, model_id=os.environ["OPENAI_MODEL"])
    if p == "bedrock":
        from strands.models import BedrockModel
        return BedrockModel(model_id=os.environ["BEDROCK_MODEL"],
                            region_name=os.getenv("AWS_REGION", "us-west-2"))
    return None


def build_agent():
    from strands import Agent
    return Agent(model=make_model(), tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT, callback_handler=None)


def _money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def _template_memo(scenario):
    """No-model path: the agent's tools in a fixed order, numbers dropped into a template."""
    f = forecast_cash_flow(scenario=scenario)
    if f["min_balance"] >= 1500:
        return (f"Problem: none. The lowest balance is {_money(f['min_balance'])} on {f['min_date']}, "
                f"above the reserve. No action needed.")
    d = find_drivers(scenario=scenario)
    p = optimize_plan(scenario=scenario, decision_date="2026-10-12")
    w = cost_of_waiting(scenario=scenario)
    drafted = [draft_action(lever_id=lv, scenario=scenario)["action"]["id"] for lv in p["levers"]] if p["feasible"] else []

    late = d["pushed_inflows"]
    cause = "; ".join(f"[{x['txn_id']}] {x['description']} arrives {x['actual_date']} instead of "
                      f"{x['planned_date']}, lowering the minimum by {_money(x['impact_on_min_balance'])}" for x in late)
    big = ", ".join(f"[{o['txn_id']}] {o['description']} {_money(o['amount'])}" for o in d["outflows"][:3])
    names = " + ".join(f"{S.LEVERS_BY_ID[i].name} ({i})" for i in p["levers"])
    plan = (f"{names} for {_money(p['total_cost'])} total; lowest balance becomes "
            f"{_money(p['forecast']['min_balance'])}." if p["feasible"] else p["note"])
    wait = "; ".join(f"decide {x['decision_date']}: " + (_money(x["total_cost"]) if x["feasible"] else "no safe plan")
                     for x in w["points"])
    return (f"Problem: cash falls to {_money(f['min_balance'])} on {f['min_date']}, "
            f"{_money(f['shortfall_vs_reserve'])} below the {_money(1500)} reserve.\n"
            f"Cause: {cause or 'scheduled outflows'}. Largest payments that day or before: {big}.\n"
            f"Cheapest plan: {plan}\n"
            f"Cost of waiting: {wait}.\n"
            f"Actions drafted: {', '.join(drafted) or 'none'} (waiting for owner approval).")


def investigate(scenario="live", question="Will we run short of cash this week? Explain why and what to do."):
    start_trace()
    mode, error = provider(), None
    memo = None
    if mode != "stub":
        try:
            agent = build_agent()
            memo = str(agent(f"Scenario: {scenario}. Question: {question}"))
            check = verify(memo, get_trace()["outputs"])
            if not check["verified"]:
                memo = str(agent("These figures are not in any tool output: "
                                 f"{check['unverified_amounts'] + check['unknown_txn_ids']}. "
                                 "Rewrite the memo using only numbers returned by the tools."))
        except Exception as exc:  # model down, bad credentials, etc. The demo must keep working.
            error, memo = f"{type(exc).__name__}: {exc}", None
    if memo is None:
        mode = "stub" if mode == "stub" else f"stub (model failed: {error})"
        memo = _template_memo(scenario)
    tr = get_trace()
    check = verify(memo, tr["outputs"])
    return {"memo": memo, "trace": tr["calls"], "verified": check["verified"],
            "unverified_amounts": check["unverified_amounts"], "cited_txn_ids": check["cited_txn_ids"],
            "mode": mode}
