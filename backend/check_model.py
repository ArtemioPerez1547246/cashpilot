"""One-command check that a real model drives the ForeCash agent.

    cd backend
    MODEL_PROVIDER=akamai AKAMAI_API_KEY=... python check_model.py

(AKAMAI_BASE_URL and AKAMAI_MODEL default to the hackathon endpoint.)
PASS means: the model answered, it called at least 3 engine tools, and every dollar figure
in its memo matches a tool output.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("AKAMAI_BASE_URL", "https://ws.akamai-workshops.com/v1")
os.environ.setdefault("AKAMAI_MODEL", "hackathon-chat")
os.environ.setdefault("CASHPILOT_STATE_DIR", tempfile.mkdtemp(prefix="cashpilot-check-"))

from app.agent import investigate  # noqa: E402

t0 = time.time()
r = investigate("disruption", "Will we run short of cash this week? Explain why and what to do.")
secs = time.time() - t0

print(f"mode:     {r['mode']}")
print(f"seconds:  {secs:.1f}")
print(f"tools:    {[t['tool'] for t in r['trace']]}")
print(f"verified: {r['verified']}  unverified: {r['unverified_amounts']}")
print(f"cited:    {r['cited_txn_ids']}")
print("-" * 60)
print(r["memo"])
print("-" * 60)

ok = r["mode"] in ("akamai", "openai", "bedrock") and len(r["trace"]) >= 3 and r["verified"]
print("PASS" if ok else "FAIL")
if secs > 30:
    print("WARNING: slower than 30 s; on stage, trigger it from the monitor before you need it.")
sys.exit(0 if ok else 1)
