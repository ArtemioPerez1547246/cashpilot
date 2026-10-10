from __future__ import annotations

import re


def extract_dollar_values(text: str) -> list[float]:
    matches = re.findall(r"\$?\d+(?:,\d{3})*(?:\.\d+)?", text)
    return [float(m.replace("$", "").replace(",", "")) for m in matches]


def extract_txn_ids(text: str) -> list[str]:
    return re.findall(r"\bT\d+\b", text)


def verify_memo(memo: str, tool_outputs: list[dict]) -> dict:
    dollar_values = extract_dollar_values(memo)
    txn_ids = extract_txn_ids(memo)
    tool_numbers = []
    for output in tool_outputs:
        if isinstance(output, dict):
            for val in output.values():
                if isinstance(val, (int, float)):
                    tool_numbers.append(float(val))
    acceptable = all(any(abs(val - num) <= 1 for num in tool_numbers) for val in dollar_values) if dollar_values else True
    return {"verified": acceptable and all(txn_id in txns for txn_id in txn_ids for txns in [set()])}
