# Protocol and State Rules

## WebSocket `/ws`

Client message: `{ "id": "uuid", "route": "reasoning|code|openclaw|research", "text": "..." }`.

Server events: `{ "type": "state", "id": "uuid", "state": "thinking|idle|error" }`, `{ "type": "answer", "id": "uuid", "text": "...", "notes": ["path.md"] }`, or `{ "type": "error", "id": "uuid", "message": "..." }`.

Client-only states are `listening`, `transcribing`, and `speaking`. Transitions: `idle → listening → transcribing → thinking → speaking → idle`, with `error` available from every step. Text input goes directly `idle → thinking`. The current socket processes requests serially; send another request after the previous answer. The face mixes state intensity with FFT bass, middle, and high bands. The microphone analyser does not route the microphone into speakers.

## HTTP

| Route | Method | Body/result |
| --- | --- | --- |
| `/api/health` | GET | Configured component indicators |
| `/api/notes?q=...` | GET | Ranked excerpts |
| `/api/graph` | GET | Nodes and resolved wiki-link edges |
| `/api/note?path=...` | GET | Full note content |
| `/api/note` | POST | `{ "path":"...md", "content":"..." }` creates only |
| `/api/stt` | POST | Multipart `file` → `{ "text":"..." }` |
| `/api/tts` | POST | `{ "text":"..." }` → WAV bytes |

The app is for a trusted local user. Note excerpts are bounded and treated as untrusted data in the model prompt. The vault adapter rejects traversal and symlinks escaping the vault. New-note creation fails for an existing file. Secrets stay in `.env` and are not sent to the browser.

## Model fallback

The `reasoning` route calls its primary once. For a 402, 408, 429, 500, 502, 503, 504, network timeout, transport error, or a recognized 400 context-length error, it calls a configured fallback once. Other errors, including authentication errors, propagate. A fallback answer is labeled. Routes `code`, `openclaw` and `research` do not silently switch providers. The Streamlit testing console uses the same model router.
