"""Checks that every dollar figure and transaction ID in a memo came from a tool output."""
import re

from ..engine import scenarios as S

_DOLLARS = re.compile(r"-?\$\s?-?\d[\d,]*(?:\.\d+)?")
_TXN = re.compile(r"\bT\d{2}\b")


def _numbers(obj, acc):
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, (int, float)):
        acc.add(round(abs(float(obj)), 2))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers(v, acc)
    return acc


def verify(memo, tool_outputs, tolerance=1.0):
    known = _numbers(tool_outputs, set())
    known |= _numbers([lv.cost_usd for lv in S.LEVERS], set())
    known |= _numbers(S.settings(), set())  # reserve and opening cash are known inputs
    unverified = []
    for m in _DOLLARS.findall(memo):
        val = abs(float(m.replace("$", "").replace(",", "").replace(" ", "")))
        if not any(abs(val - k) <= tolerance for k in known):
            unverified.append(m.strip())
    ids = {t.id for t in S.BASE}
    cited = sorted(set(_TXN.findall(memo)))
    bad_ids = [i for i in cited if i not in ids]
    return {"verified": not unverified and not bad_ids, "unverified_amounts": unverified,
            "unknown_txn_ids": bad_ids, "cited_txn_ids": [i for i in cited if i in ids]}
