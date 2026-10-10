from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ToolTrace:
    tool: str
    input: dict
    output_summary: str
    ms: int


def build_agent():
    return {
        "status": "stubbed",
        "provider": os.getenv("MODEL_PROVIDER", "stub"),
        "tools": ["get_transactions", "forecast_cash_flow", "find_drivers", "optimize_plan", "cost_of_waiting", "draft_action"],
        "system_prompt": "Never calculate numbers yourself. Use tool outputs for every dollar value and cite transaction IDs with brackets.",
    }
