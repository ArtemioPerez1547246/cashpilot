# ForeCash × DevRev Computer: commitment-to-action connector

**Problem.** Promises made to customers on calls ("we'll send the revised SOW by Friday") get lost
between the call and the task tracker, or get tracked twice, or get tracked without proof of what
was actually promised.

**Solution.** One MCP connector with two halves: read-only Enterprise-Bench evidence tools (adapted from DevRev's Evidence Vault starter) and an approval-gated follow-up board. A DevRev Computer skill (`skills/commitment-to-action/SKILL.md`) finds explicit
commitments for any account in the Enterprise-Bench data, shows a preview with source evidence,
and, only after the user approves, creates tracked tasks on the ForeCash follow-up board through
our MCP connector. Re-running it never creates duplicates. Any teammate with their own connection
can run it on any account.

**Data.** DevRev's team confirmed we may load our own data for our use case. The evidence files in
`devrev/sample-data/` are synthetic call transcripts and accounts written for this demo, consistent with
ForeCash's Paletería Arkansas demo data (for example, Ridgeline Corp's INV-2041 for $4,000). Every file is
marked `"synthetic": true`. The board stores only
follow-ups derived from it, in its own database (`devrev_board.db`). It never reads or writes
ForeCash's cash data, forecast, or action queue.

## Architecture
DevRev Computer + skill → HTTPS `https://DOMAIN/mcp` (Bearer token, Streamable HTTP, Caddy on our
Akamai Linode) → `board` container (`backend/app/devrev_board/server.py`) → SQLite on the shared
state volume → ForeCash dashboard, view "Enterprise follow-ups (DevRev)".

## Tools
| Tool | What it does | Computer access mode |
|---|---|---|
| `list_sources(prefix, offset, limit)` | Enterprise-Bench export files (transcripts, CRM, PM, KB, internal docs) | Always allow |
| `search_evidence(query, prefix, offset, limit)` | Literal search, one hit per file, with sha256 + line | Always allow |
| `read_evidence(path, start_line, max_lines)` | Bounded read; cite path + sha256 + line range | Always allow |
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

## Observed tests (run in DevRev Computer on Oct 10, 2026)
| Test | Who | Account | Result |
|---|---|---|---|
| Positive run, approve 1 task | builder | Ridgeline Corp | Pass: 5 commitments previewed with file, lines and quote; Oct 15 date treated as superseded by the Oct 21 call; approved item created as F001 |
| Same request again: no duplicate | builder | Ridgeline Corp | Pass: `created: false`, same F001, repeat counted |
| Decline the preview: nothing created | builder | Coldline Freezers | Pass: board unchanged |
| Account with no commitments | builder | Bluebonnet Elementary PTA | Pass: read the full transcript, explained why each line is not a promise, created nothing |
| Ambiguous account name | builder | "Ridgeline" | Pass: listed Ridgeline Corp and Ridgeline Events LLC with IDs and asked which |
| Second teammate, own connection, different account | teammate | Sierra Dairy Co-op | _fill in_ |
| Board, evidence and website-promise unit tests | CI | n/a | 15 passed (7 board, 4 evidence, 4 promise flow) |

## Known limits
- One shared team token, not per-user authorization; `requested_by` is reported by the caller, not verified.
- The board does not re-check source IDs against the dataset; the skill must cite real records.
- Literal search in transcripts can miss paraphrased commitments; the skill reports coverage limits.
- Observed miss: on Ridgeline Corp the skill did not list our own promise to send a statement copy
  (MTG-1008-RIDGE, 01:20).
- Observed deviation: on Coldline Freezers it kept a conditional offer ("hold until Oct 21 if you tell
  us by Oct 13") as a proposed item instead of an open question. It stated the condition and asked first.
- Promises recorded from the website are the owner's notes of a verbal statement, labeled as such;
  they are weaker evidence than a transcript.
