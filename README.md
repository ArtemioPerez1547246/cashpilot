# CashPilot

Finds the cheapest way through a small business's cash crunch, and shows what it costs to wait.
Hack Midwest 2026. Demo business: Paletería El Sol (synthetic data).

## Layout

| Path | What | Owner |
| --- | --- | --- |
| `backend/app/engine/` | Deterministic math: forecast, drivers, optimizer, cost of waiting. No AI. | Irvin |
| `backend/app/engine/scenarios.py` | Which transactions the engine sees: normal, disruption, live | Irvin |
| `backend/app/agent/` | Strands agent: 6 tools, prompt, verifier, model switch | Glenn |
| `backend/app/actions/` | Approval queue (SQLite, no duplicates) + message drafts | Glenn |
| `backend/app/monitor.py` | Events → forecast → alert → background investigation | Isaac |
| `backend/app/main.py` | FastAPI routes (see API.md) | all |
| `frontend/app.py` | Streamlit dashboard | Irvin |
| `deploy/` | Docker Compose + Caddy for the Akamai Linode | Isaac |
| `backend/data/` | `cashpilot_dataset.json` (transactions), `levers.json` | Julian |

## Run locally

```bash
pip install -r backend/requirements.txt
cd backend && python -m pytest -q            # must stay green
uvicorn app.main:app --reload --port 8000     # API
# second terminal, repo root:
API_BASE=http://localhost:8000 streamlit run frontend/app.py
```

## Model

`MODEL_PROVIDER=stub` (default) runs the same tools in a fixed order and fills a template memo.
Set `akamai` or `bedrock` plus the variables in `deploy/.env.example` to use a real model.
Every response says which mode produced the memo.

## Deploy (on the Linode)

```bash
git clone <repo> && cd cashpilot
cp deploy/.env.example deploy/.env   # fill in DOMAIN and model keys
./deploy/deploy.sh
```

## Rules

- Agents never do arithmetic. Every dollar figure comes from the engine; the verifier checks the memo.
- Nothing executes automatically. The agent drafts; the owner approves.
- Run `pytest` before every push. Never commit `.env`.
