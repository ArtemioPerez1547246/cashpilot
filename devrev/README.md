# CashPilot × DevRev Computer: commitment-to-action connector

**Problem.** Promises made to customers on calls ("we'll send the revised SOW by Friday") get lost
between the call and the task tracker, or get tracked twice, or get tracked without proof of what
was actually promised.

**Solution.** A DevRev Computer skill (`skills/commitment-to-action/SKILL.md`) finds explicit
commitments for any account in the Enterprise-Bench data, shows a preview with source evidence,
and, only after the user approves, creates tracked tasks on the CashPilot follow-up board through
our MCP connector. Re-running it never creates duplicates. Any teammate with their own connection
can run it on any account.

**Data boundary.** Business evidence comes only from Enterprise-Bench. The board stores only
follow-ups derived from it, in its own database (`devrev_board.db`). It never reads or writes
CashPilot's cash data, forecast, or action queue.

## Architecture
DevRev Computer + skill → HTTPS `https://DOMAIN/mcp` (Bearer token, Streamable HTTP, Caddy on our
Akamai Linode) → `board` container (`backend/app/devrev_board/server.py`) → SQLite on the shared
state volume → CashPilot dashboard, view "Enterprise follow-ups (DevRev)".

## Tools
| Tool | What it does | Computer access mode |
|---|---|---|
| `list_follow_ups(account, status, limit, offset)` | Existing tasks, paged | Always allow |
| `get_follow_up(follow_up_id)` | One task; used to recover after a timeout | Always allow |
| `preview_follow_up(account, title, sources[], details, owner, due_date, requested_by)` | Validates and returns exactly what would be created + `idempotency_key` + `duplicate_of`. Writes nothing | Always allow |
| `create_follow_up(..., idempotency_key)` | Creates once; same key returns the existing task (`created: false`) | **Needs approval** |

Rules enforced server-side: at least one source reference per task; owner and due date are stored
as "not documented" when the source does not state them; due dates must be `YYYY-MM-DD`;
idempotent creation inside a single SQLite write transaction.

## Setup
1. On the Linode, add a secret to `deploy/.env`:
   `MCP_TOKEN=` + output of `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. `./deploy/deploy.sh`, then:
   `cd deploy && docker compose --env-file .env exec board python -m app.devrev_board.smoke_test https://DOMAIN/mcp`
   Expect ALL PASS.
3. DevRev admin: Settings > Integrations > AirSyncs > + Add connector > Add custom MCP server.
   URL `https://DOMAIN/mcp`, slug `team-cashpilot-followup-board`, auth = Personal Access Token
   (paste MCP_TOKEN in the secure form only). Set access modes as in the table above.
4. Each user: Settings > My Computer > Connectors, connect it with their own connection.
5. Add the skill: Settings > My Computer > Skills > Add Skill (upload `skills/commitment-to-action`).
   Org admin can push it to the team via Agent Admin > Skills once it passes the tests below.

## Observed tests (fill in with real results before submitting)
| Test | Who | Account | Result |
|---|---|---|---|
| Positive run, approve 1 task | builder | | |
| Same request again: no duplicate | builder | | |
| Decline the preview: nothing created | builder | | |
| Account with no commitments | builder | | |
| Ambiguous account name | builder | | |
| Second teammate, own connection, different account | teammate | | |
| Board unit tests (`pytest tests/test_devrev_board.py`) | CI | n/a | 7 passed |

## Known limits
- One shared team token, not per-user authorization; `requested_by` is reported by the caller, not verified.
- The board does not re-check source IDs against the dataset; the skill must cite real records.
- Literal search in transcripts can miss paraphrased commitments; the skill reports coverage limits.
