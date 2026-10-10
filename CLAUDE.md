# CashPilot: team context for any AI assistant

Paste this file into a new Claude chat (or open the repo in Claude Code, which reads it
automatically) to get the full project context. Keep it current: it is the shared memory.

## What we are building
Hack Midwest 2026, Kansas City. Submission due **Sun Oct 11, 8:00 AM** (a **video**); live demos at
9:00 AM (3 minutes, **no slides at all**, show the product only).

**CashPilot** finds the cheapest way through a small business's cash crunch, and shows what it
costs to wait. Demo business: **Paletería El Sol** (synthetic data, re-skinned from a verified
restaurant dataset; every dollar amount and date unchanged).

Pitch line: *"Decide Monday: $9. Decide Wednesday: $125. Wait until Friday: you miss payroll."*

## Golden numbers (the app must show exactly these)
- Window Oct 12–18 (7 days), opening cash $8,000, minimum reserve $1,500.
- Normal week: ending $2,000, lowest $1,800 on Oct 16 (payroll day). Safe.
- Disruption (Ridgeline catering invoice T08 paid 6 days late): lowest **-$2,200** on Oct 16.
- Deferring the freezer alone (L01): ending +$500 but lowest **$300**, still below the reserve.
- Cheapest safe plan decided Oct 12: **L01 + L05B ($2,000 credit draw) = $9.21**.
- Decided Oct 14: **$124.60**. Decided Oct 16: **no safe plan** (payroll missed).

## Prizes we target (one team can win several)
1. **Flex, Best FinTech**: no Flex API needed; the optimizer with real financing costs is the fintech.
2. **AWS, Best use of Strands Agents**: the agent in `backend/app/agent/` with a visible tool trace.
3. **Akamai Cloud AI**: app runs on an Akamai Linode; model via Akamai hosted inference.
4. **DevRev** (optional, after 7 PM): separate workflow on the Enterprise-Bench dataset only.

## Hard rules
- **Agents never do arithmetic.** Every dollar figure comes from the engine; `agent/verifier.py` checks the memo.
- **Nothing executes automatically.** The agent drafts actions; the owner approves.
- **Never commit secrets** (API keys, tokens, passwords). Keys go only in `deploy/.env` on the server
  or in `export` in your terminal. Run `git status` before every push.
- Run `cd backend && python -m pytest -q` before every push (29 tests must pass).
- Commit with normal `git`. Do not use tools that write files through the GitHub API (that broke the repo once).
- Never claim something works without showing it running.

## Team
| Person | Role | Owns |
| --- | --- | --- |
| Julian | Product lead, finance, QA, pitch | Decisions, data, tracker, demo, video narration |
| Glenn (CS) | Agent lead, then DevRev | `backend/app/agent/`, `actions/`, model setup |
| Irvin (IE) | Engine lead, then dashboard | `backend/app/engine/`, `frontend/app.py` |
| Isaac (EE) | Platform | Akamai Linode, `deploy/`, monitor, DevRev help, video setup |

Plan doc with tracker (source of truth for status):
https://claude.ai/code/artifact/0b54d176-3d7a-4b7e-bc4f-b366e29f0f2e

## Code map
- `backend/app/engine/`: forecast, drivers, optimizer, cost of waiting (pure Python). `scenarios.py` picks normal / disruption / live.
- `backend/app/agent/`: Strands agent, 6 tools, prompt, verifier, model switch (`MODEL_PROVIDER` = stub | akamai | bedrock | openai).
- `backend/app/actions/`: approval queue (SQLite, idempotent) + message templates.
- `backend/app/monitor.py`: event → forecast → alert → background investigation.
- `backend/app/main.py`: FastAPI routes, documented in `API.md`.
- `frontend/app.py`: Streamlit dashboard.
- `deploy/`: Dockerfile, Compose (api, ui, Caddy HTTPS via sslip.io), `deploy.sh`, `.env.example`.
- `backend/check_model.py`: prints PASS when a real model drives the agent.

## Run locally
Mac:
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --port 8000          # window 1
streamlit run ../frontend/app.py          # window 2 (activate the venv first)
```
Windows PowerShell: same, but `py -m venv .venv` and `.venv\Scripts\Activate.ps1`
(if scripts are blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`).

Real model: `export MODEL_PROVIDER=akamai` and `export AKAMAI_API_KEY=...` (never write the key in a file in the repo).

## Demo path (3 minutes)
Reset demo → "Ridgeline pays 6 days late" → alert appears with no typed question → memo with cited
IDs and tool trace → pick only the freezer lever: still $300, below reserve → cheapest plan $9.21 →
cost of waiting $9.21 / $124.60 / no safe plan → approve one drafted action.

## Open questions
- Video length limit and upload platform.
- What the 7 PM checkpoint requires.
- Whether a DevRev workflow counts as part of our one project.
