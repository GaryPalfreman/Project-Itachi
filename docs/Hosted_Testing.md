# Hosted Testing on Streamlit Community Cloud

The hosted console contains text chat, autonomous read-only research and model failover. It does not import notes, connect personal accounts, run arbitrary commands or mount local files. The audio-reactive face is served by the local FastAPI app in [[Deployment_Mac]].

## Deployment

1. Select repository `GaryPalfreman/Project-Itachi`, branch `main`, main file `streamlit_app.py`, Python 3.12.
2. Set the app's viewing access to **private** before adding provider credentials. Add a strong independent `ITACHI_ACCESS_PASSCODE` in app secrets as an additional access gate.
3. Add one compatible model endpoint or an ordered provider list. The app cannot reach Ollama at `127.0.0.1` on another computer.
4. Optionally add `ITACHI_TAVILY_KEY` for internet research. Check **Allow internet searches for this question** when derived search terms may leave the app.

Example secrets (replace placeholders with independently authorized provider details):

```toml
ITACHI_ACCESS_PASSCODE = "GENERATE_A_NEW_RANDOM_PASSPHRASE"
ITACHI_MODEL_ROUTES_JSON = '[{"name":"primary","url":"https://PROVIDER_ONE/v1","model":"MODEL_ONE","key":"PROVIDER_ONE_KEY"},{"name":"backup","url":"https://PROVIDER_TWO/v1","model":"MODEL_TWO","key":"PROVIDER_TWO_KEY"}]'
ITACHI_TAVILY_KEY = "OPTIONAL_WEB_SEARCH_KEY"
```

For a single provider, use `ITACHI_REASONING_URL`, `ITACHI_REASONING_MODEL` and `ITACHI_REASONING_KEY`. Up to five model routes are supported. Quota, timeout, context and selected server failures can trigger failover; invalid credentials do not. Each provider has its own rates and limits.

## Autonomous research

The model chooses up to three read-only actions from `web_search` and `calculate`, then synthesizes an answer. Internet access also requires the web checkbox and Tavily key. The tools cannot edit files, run commands, access accounts or escalate privileges. See [[Autonomy_and_Permissions]].
