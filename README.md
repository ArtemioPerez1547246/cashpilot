# ForeCash

*ForeCash: forecast your cash.*

**Finds the cheapest way through a small business's cash crunch, and shows what it costs to wait.**

> Decide Monday: **$9.21**. Decide Wednesday: **$124.60**. Wait until Friday: **you miss payroll.**

Hack Midwest 2026 · Demo business: **Paletería Arkansas** (synthetic data) ·
Live: <https://172-237-149-215.sslip.io>

## What it does

A customer tells the owner they'll pay late. ForeCash moves the payment in the forecast, sees that
payroll on Friday Oct 16 now leaves the business at **−$2,200** (reserve: $1,500), finds the cheapest
safe plan out of every combination of 10 financing and timing options, prices what each day of
waiting costs, and drafts the messages to send. A Strands agent explains it in plain language, and
every dollar figure it writes is checked against the engine. Nothing is sent until the owner approves.

## How we meet each sponsor challenge

| Sponsor | What we built | Where to see it | Code |
|---|---|---|---|
| **Flex · Best FinTech** | An optimizer that prices real financing costs (credit line at 12% APR, invoice advance fee, merchant cash advance factor rate, late fees, free reschedules) and tests every combination to keep **every day** above the reserve. Cost of waiting: $9.21 → $124.60 → no safe plan. | "Cheapest plan" + "How ForeCash priced every option" + "What waiting costs you" | `backend/app/engine/` |
| **AWS · Best use of Strands Agents** | A Strands agent with 6 tools (forecast, drivers, optimizer, cost of waiting, transactions, draft action). A verifier checks every dollar amount and transaction ID in the memo against tool outputs and asks the agent to rewrite if any don't match. Visible tool trace. | "What happened and why" → ✓ badge + "tool trace" | `backend/app/agent/` |
| **Akamai · Cloud AI** | Runs on an Akamai Linode (Docker Compose + Caddy HTTPS). The agent's model is Akamai hosted inference (`hackathon-chat`). The DevRev MCP connector is served from the same box. | Live URL · "AI on Akamai" pill | `deploy/`, `backend/app/agent/agent.py` |
| **DevRev · Computer** | A combined build: one MCP connector (7 tools: read-only evidence search + an approval-gated follow-up board with idempotency) and a reusable Computer skill that turns customer promises in call transcripts into tracked follow-ups with file, line range and sha256. The owner can also record a promise from the website. Tested end to end in Computer (results in `devrev/README.md`). | ☰ → New / View → "(DevRev)" · DevRev panel under the alert · "Enterprise follow-ups (DevRev)" view | `devrev/`, `backend/app/devrev_board/` |

## How it fits together

```
Owner hears "we'll pay on the 21st"          DevRev Computer + commitment-to-action skill
 (☰ New → Late Receivable)                    (finds the promise in a call transcript)
            │                                              │  MCP over HTTPS (/mcp, Bearer token)
            ▼                                              ▼
   FastAPI backend on Akamai Linode ── follow-up board (SQLite, idempotent) ── evidence tools
            │
            ├─ engine: forecast → drivers → optimizer → cost of waiting   (deterministic, no AI)
            ├─ monitor: event → alert → background investigation
            ├─ Strands agent (Akamai inference) → memo → verifier
            └─ approval queue (drafts only, no duplicates)
            │
            ▼
   Streamlit dashboard: alert · chart · cheapest plan · cost of waiting · DevRev evidence · approvals
```

## Demo (3 minutes)

1. **Reset demo** → "You're safe this week."
2. ☰ → New → **Late Receivable** → T08 Ridgeline, Oct 21, Luis Pardo → Preview → Approve
   (or press **Simulate: Ridgeline pays 6 days late**).
3. Red alert: **−$2,200 on Fri Oct 16**. The DevRev panel shows the customer's own words with the source.
4. Try a fix → only the freezer deferral → ending cash looks fine, but the lowest day is still **$300**.
5. Cheapest safe plan **$9.21**; cost of waiting **$9.21 / $124.60 / no safe plan**.
6. The Strands memo (✓ verified, tool trace) → approve one drafted action.

## Rules we hold ourselves to

- Agents never do arithmetic. Every dollar figure comes from the engine; the verifier checks the memo.
- Nothing executes automatically. The agent and DevRev draft; the owner approves.
- Synthetic data only. No secrets in the repo; keys live in `deploy/.env` on the server.

## Run locally

```bash
pip install -r backend/requirements.txt
cd backend && python -m pytest -q            # 44 tests, all must pass
uvicorn app.main:app --reload --port 8000     # API
# second terminal, repo root:
API_BASE=http://localhost:8000 streamlit run frontend/app.py
```

`MODEL_PROVIDER=stub` (default) runs the same tools in a fixed order with a template memo. Set
`akamai` (or `bedrock` / `openai`) plus the variables in `deploy/.env.example` to use a real model.
Every memo says which mode produced it.

## Deploy (on the Linode)

```bash
git clone <repo> && cd cashpilot
cp deploy/.env.example deploy/.env   # DOMAIN, MODEL_PROVIDER, AKAMAI_API_KEY, MCP_TOKEN
./deploy/deploy.sh
```

## Layout

| Path | What | Owner |
| --- | --- | --- |
| `backend/app/engine/` | Forecast, drivers, optimizer, cost of waiting. No AI. | Irvin |
| `backend/app/agent/` | Strands agent, tools, prompt, verifier, model switch | Glenn |
| `backend/app/actions/` | Approval queue (SQLite, no duplicates) + message drafts | Glenn |
| `backend/app/monitor.py` | Events → forecast → alert → background investigation | Isaac |
| `backend/app/devrev_board/` | DevRev MCP server, evidence tools, follow-up board, owner promises | Glenn, Irvin |
| `devrev/` | Computer skill, synthetic transcripts, DevRev README | Glenn, Irvin |
| `frontend/app.py` | Streamlit dashboard | Irvin |
| `deploy/` | Docker Compose + Caddy for the Akamai Linode | Isaac |
| `backend/data/` | Transactions and financing options | Julian |

API reference: [`API.md`](API.md). DevRev setup, tools, tests and limits: [`devrev/README.md`](devrev/README.md).
