# Master Architecture Blueprint

Project: [[Itachi]] · Status: runnable local prototype · Revision: 2026-09-25

## System boundary

The FastAPI process listens on `127.0.0.1:8765`. It serves the UI, WebSocket, vault API, and speech API from one origin. Keep it local while the vault and OpenClaw gateway credentials are attached. For access from another device, use an authenticated private tunnel or reverse proxy, TLS, and a separate access control layer before changing the bind address.

| Layer | File | Contract |
| --- | --- | --- |
| Node face | `frontend/face.js` | Canvas points and near-neighbor edges; states and frequency bands |
| Audio | `frontend/audio.js` | `getUserMedia` → MediaRecorder → STT; WAV playback → AudioContext analyser |
| Transport | `backend/app/main.py` | `/ws`, `/api/stt`, `/api/tts`, `/api/note` |
| Models | `backend/app/orchestration.py` | OpenAI-compatible `/v1/chat/completions` |
| Vault | `backend/app/vault.py` | Markdown search/read/new-note creation under configured root |

## Data flows

1. Prompt: UI → `/ws` → selected route → answer event → UI. Autonomous mode plans bounded research steps. Knowledge retrieval is disabled unless explicitly configured.
2. Voice in: microphone analyser drives the face; browser records a clip; `/api/stt` transcribes locally; recognized text enters the prompt flow.
3. Voice out: `/api/tts` generates WAV locally; browser analyser reads the playback signal and drives the face.
4. Vault write: an explicit `POST /api/note` creates a new `.md` note. Conversation replies never write notes implicitly.

## Model routes

- `reasoning`: a local Nemotron model behind an OpenAI-compatible endpoint. Default Ollama address `http://127.0.0.1:11434/v1` and model `nemotron-mini:4b`.
- `fallback`: optional separate Llama or other compatible model. The reasoning route makes one bounded failover attempt on quota, context-length or availability errors. For hosted testing, both configured endpoints must be reachable from the cloud. See [[Hosted_Testing]].
- `code`: separately configured coding endpoint; a Codex login is not automatically an HTTP model endpoint.
- `openclaw`: existing gateway's optional HTTP chat completions endpoint. Requires an enabled endpoint and operator token on the same machine.
- `research`: an **unverified** JEV adapter. `ITACHI_JEV_URL` must accept `{ "query": "..." }` and return `{ "answer": "...", "sources": [...] }`. This is an Itachi adapter contract, not a claim about JEV's native API.

## Knowledge graph convention

Use YAML frontmatter with `type`, `machine`, `process`, `revision`, `source`, and `verified_at`; connect related notes with Obsidian `[[Wiki_Links]]`. Search currently uses text scoring and stores no separate vector index. It does not infer relationships, synchronize with a remote vault, or modify existing notes. See [[Protocol_and_State_Rules]] and [[Deployment_Mac]].
