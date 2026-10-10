# CashPilot API

All routes are under `/api` and return JSON. `scenario` is one of `normal`, `disruption`, `live`
(default `live`, which starts as `normal` and changes when events arrive). Unknown IDs return 404.

| Method | Path | Body / query | Returns |
| --- | --- | --- | --- |
| GET | `/api/health` | | `{ok, model_provider, version}` |
| GET | `/api/scenarios` | | scenarios with their changes |
| GET | `/api/levers` | | every lever with cost, constraint, deadline |
| GET | `/api/transactions` | `?scenario=` | transactions as that scenario sees them |
| GET | `/api/overview` | `?scenario=` | `{settings, forecast, upcoming_obligations}` |
| GET | `/api/forecast` | `?scenario=` | ForecastResult |
| POST | `/api/simulate` | `{scenario, lever_ids, decision_date, extra_changes}` | ForecastResult with those levers |
| POST | `/api/optimize` | `{scenario, decision_date}` | Plan (cheapest safe set of levers, or honest `feasible:false`) |
| GET | `/api/cost-of-waiting` | `?scenario=` | plans decided today, +2 and +4 days |
| GET | `/api/drivers` | `?scenario=` | what causes the dip, with transaction IDs |
| POST | `/api/investigate` | `{scenario, question}` | `{memo, trace, verified, unverified_amounts, cited_txn_ids, mode}` |
| POST | `/api/events` | `{type: "payment_delayed", txn, days}` | `{alert, forecast}`; investigation runs in background |
| GET | `/api/alerts` | | alerts, newest first, with investigation when ready |
| GET | `/api/actions` | | approval queue |
| POST | `/api/actions/{id}/approve` | | action (deciding twice changes nothing) |
| POST | `/api/actions/{id}/reject` | | action |
| POST | `/api/demo/reset` | | clears live events, alerts and actions |

Golden results (disruption: Ridgeline pays 6 days late): lowest balance -$2,200 on Oct 16;
freezer deferral alone leaves $300 (below the $1,500 reserve); cheapest plan decided Oct 12 is
L01 + L05B for $9.21; decided Oct 14 it costs $124.60; decided Oct 16 there is no safe plan.
