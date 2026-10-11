"""Strands guardrail hooks: the engine decides, the agent can't go beyond it.

A BeforeToolCallEvent hook runs before every tool call and can cancel it with a message the model sees:
  1. draft_action is allowed only for levers in the engine's latest feasible plan (optimize_plan output).
  2. Each tool can be called at most a few times per investigation (stops loops and runaway cost).
Every cancellation is written to the tool trace, so the dashboard shows what was blocked and why.
"""
LIMITS = {"draft_action": 4}
DEFAULT_LIMIT = 3


def decide(tool_name, tool_input, trace, counts):
    """Return None to allow the call, or a message explaining why it is blocked. Pure: easy to test."""
    counts[tool_name] = counts.get(tool_name, 0) + 1
    if counts[tool_name] > LIMITS.get(tool_name, DEFAULT_LIMIT):
        return f"Limit reached for {tool_name}. Use the results you already have."
    if tool_name == "draft_action":
        plans = [out for c, out in zip(trace["calls"], trace["outputs"]) if c["tool"] == "optimize_plan"]
        if not plans:
            return "Call optimize_plan first. Actions can only be drafted for levers in the engine's plan."
        plan = plans[-1]
        if not plan.get("feasible"):
            return "There is no safe plan, so no actions can be drafted. Say so in the memo."
        lever = (tool_input or {}).get("lever_id")
        if lever not in plan.get("levers", []):
            return f"{lever} is not in the engine's cheapest plan {plan.get('levers')}. Draft only those levers."
    return None


def make_hooks(get_trace):
    """Build the Strands HookProvider. Returns [] if this Strands version has no hooks (agent still works)."""
    try:
        from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry
    except Exception:
        return []

    class Guardrails(HookProvider):
        def __init__(self):
            self.counts = {}

        def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
            registry.add_callback(BeforeToolCallEvent, self.check)

        def check(self, event: BeforeToolCallEvent) -> None:
            name = event.tool_use.get("name", "")
            msg = decide(name, event.tool_use.get("input") or {}, get_trace(), self.counts)
            if msg:
                event.cancel_tool = msg
                tr = get_trace()
                tr["calls"].append({"tool": "guardrail", "input": {"blocked": name},
                                    "output_summary": f"blocked {name}: {msg}", "ms": 0})
                tr["outputs"].append({})

    return [Guardrails()]
