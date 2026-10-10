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
    bad_days = wrong_weekdays(memo)
    return {"verified": not unverified and not bad_ids and not bad_days,
            "unverified_amounts": unverified + bad_days,
            "unknown_txn_ids": bad_ids, "cited_txn_ids": [i for i in cited if i in ids]}


_DAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
           "sep": 9, "oct": 10, "nov": 11, "dec": 12}
# a date (2026-10-16, 10-16, 10/16, Oct 16) with a weekday name within a few characters of it
_DATE = r"(?:(\d{4})-)?(\d{1,2})[-/](\d{1,2})|(" + "|".join(_MONTHS) + r")[a-z]*\.?\s+(\d{1,2})"
_PAIR = re.compile(rf"(?:({_DAYS})\W{{1,4}}(?:{_DATE}))|(?:(?:{_DATE})\W{{1,4}}({_DAYS}))", re.I)


def wrong_weekdays(memo):
    """Weekday names that do not match the date right next to them (e.g. '2026-10-16 (Monday)')."""
    import datetime as dt
    bad = []
    for m in _PAIR.finditer(memo):
        g = m.groups()
        name = g[0] or g[11]
        if g[0]:
            y, mo, d, mname, md = g[1:6]
        else:
            y, mo, d, mname, md = g[6:11]
        try:
            month = int(mo) if mo else _MONTHS[mname.lower()[:3]]
            day = int(d) if d else int(md)
            actual = dt.date(int(y or S.START[:4]), month, day).strftime("%A")
        except (ValueError, KeyError, TypeError):
            continue
        if actual.lower() != name.lower():
            bad.append(f"{m.group(0).strip()} (is a {actual})")
    return bad
