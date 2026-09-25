# Hosted Testing on Streamlit Community Cloud

This is a temporary **testing console**. The full audio-reactive face, WebSocket transport, Piper voice, and local Obsidian write tools remain in the FastAPI app described in [[Deployment_Mac]]. The hosted console has text chat, a small visual pulse, a read-only ZIP import, and model fallback. It does not need a local GPU.

## Deploy

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
2. Choose **Create app → Deploy a public app from GitHub** (repository visibility and app viewing access are separate settings).
3. Repository: `GaryPalfreman/Project-Itachi`; branch: `main`; main file path: `streamlit_app.py`.
4. In **Advanced settings**, select Python 3.12 and add secrets for a model endpoint reachable from the cloud. The app cannot reach `127.0.0.1` on your Mac. Start with no secrets to test the interface and search-only mode.
5. Set app viewing access to **private** before uploading engineering notes. If private access is unavailable for your account, test only with nonsensitive notes. Once deployed, check the chat, upload a small Markdown ZIP, and ask for a term within it.

Cloud secrets example (replace the provider, model and key with credentials **you** control):

```toml
ITACHI_REASONING_URL = "https://YOUR_PROVIDER/v1"
ITACHI_REASONING_MODEL = "YOUR_MODEL"
ITACHI_REASONING_KEY = "YOUR_PRIVATE_KEY"
ITACHI_FALLBACK_URL = "https://api.groq.com/openai/v1"
ITACHI_FALLBACK_MODEL = "llama-3.3-70b-versatile"
ITACHI_FALLBACK_KEY = "YOUR_GROQ_KEY"
```

The Groq Llama URL and model are an **example**, not an account connection. Verify the model is available in your account. The router makes one fallback attempt on quota/rate limit (402/429), timeout, transport outage, selected server errors, or a recognized context-limit error. It does not fail over on invalid credentials or silently continue without an answer. A fallback also has its own rate limits; it cannot provide unlimited tokens. See [[Protocol_and_State_Rules]].

## Obsidian export

On the Mac, copy only the Markdown notes you want to test into a staging folder and ZIP that folder. The import ignores `.obsidian`, non-Markdown files and traversal paths. It is limited to 2,000 notes, 30 MB of ZIP bytes, 50 MB uncompressed, and 256 KB per note. The app keeps note text in the Streamlit server session and sends relevant excerpts in prompts to the selected model provider. Clear the session when finished. It does not upload or synchronize your real `~/Documents/Engineering-Knowledge` vault automatically.

The live vault described in your engineering notes uses **separate** `PROVENANCE` (DOCUMENTED, OBSERVED, MEASURED, REPORTED, INFERRED, UNKNOWN) and `KNOWLEDGE_STATUS` (RESEARCHED, VERIFIED, STANDARD-DEPENDENT, FIELD-VALIDATED) fields. The testing console preserves source text as-is and does not upgrade either classification. Do not put employer-confidential documents into the public GitHub repository.

## Later continuous web deployment

For a persistent web version of the complete FastAPI UI, deploy the existing server on a private Docker host with authentication, TLS and durable private storage. Streamlit Community Cloud is suited to testing the text workflows, but does not mount the vault on your Mac. Keep the same model routing and explicit knowledge import boundaries.
