# Agent Assignments

The assignment sheet defines work products; it is not a record that these external agents executed.

| Agent | Work product | Acceptance check |
| --- | --- | --- |
| ChatGPT + Nemotron | Architecture, state transitions, prompt reasoning | Test model reply and vault citation |
| Codex | Backend, frontend, route tests, mathematical mesh | Run unit tests and a local browser smoke test |
| OpenClaw | Optional agent routing and locally authorized tools | Gateway request succeeds with a token; no public exposure |
| JEV AI | Source finding, source URL and date capture | Adapter response matches documented Itachi JSON contract |

For OpenClaw, enable its chat completions endpoint using its current configuration reference, confirm `curl` locally, then set `ITACHI_OPENCLAW_URL=http://127.0.0.1:18789/v1` and the operator token. Do not copy its gateway token into frontend JavaScript. [[Deployment_Mac]] has the integration checklist.
