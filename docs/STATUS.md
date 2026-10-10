# CashPilot status log

## Sat 1:05 PM — repo repair (branch fix/repo-repair)
- Commits 13642e8..5405254 on main had scrambled files (code saved under the wrong names, 8 file
  names containing code). Tests failed and the repo could not be cloned on Windows/Mac.
- Restored the clean engine from 26472f1 ("add lever optimizer, cost of waiting, reference tests").
- Rebuilt API, agent, actions, monitor, Streamlit and deploy files cleanly against that engine.
- Data re-skinned to Paletería El Sol; every dollar amount and date unchanged.
- `pytest`: 29 passed (19 engine + 10 API/agent/monitor). Dashboard renders with no errors.

## Done
- [x] Engine: forecast, drivers, optimizer, cost of waiting (golden tests)
- [x] API routes per API.md
- [x] Agent tools + trace + verifier; stub mode works with no model
- [x] Approval queue with no duplicates
- [x] Monitor: event → alert → background investigation
- [x] Streamlit dashboard shell

## Next
- [ ] Glenn: set MODEL_PROVIDER=akamai or bedrock and confirm a real model drives the tools
- [ ] Isaac: deploy to the Linode with deploy/deploy.sh; public HTTPS URL
- [ ] Irvin: polish the dashboard
