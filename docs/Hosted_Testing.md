# Hosted Testing on Streamlit Community Cloud

The hosted console contains text chat, autonomous read-only research and model failover. It does not import notes, connect personal accounts, run arbitrary commands or mount local files. The audio-reactive face is served by the local FastAPI app in [[Deployment_Mac]].

## Deployment

1. Select repository `GaryPalfreman/Project-Itachi`, branch `main`, main file `streamlit_app.py`, Python 3.12.
2. Set the app's viewing access to **private** before adding provider credentials. Add a strong independent `ITACHI_ACCESS_PASSCODE` in app secrets as an additional access gate.
3. Add one compatible model endpoint or an ordered provider list. Alternatively set `ITACHI_HF_TOKEN` to discover currently advertised free, live chat models, or `ITACHI_NVIDIA_API_KEY` for NVIDIA's currently available hosted Nemotron trial endpoint. Both keys require their own account and are subject to provider terms and limits. The app cannot reach Ollama at `127.0.0.1` on another computer.

You can also add `ITACHI_GROQ_API_KEY` for Groq's Qwen route or `ITACHI_OPENROUTER_API_KEY` for OpenRouter's free-model router. These are optional server-side secrets from separate provider accounts; their free allowances and models may change. Routes are capped at five. See [[Free_Provider_Assessment]].
4. Optionally add `ITACHI_TAVILY_KEY` for broader internet research. Without a key, enabled internet lookup uses public Wikipedia and GitHub APIs. Check **Allow internet searches for this question** when derived search terms may leave the app.

Example secrets (replace placeholders with independently authorized provider details):

```toml
ITACHI_ACCESS_PASSCODE = "GENERATE_A_NEW_RANDOM_PASSPHRASE"
ITACHI_MODEL_ROUTES_JSON = '[{"name":"primary","url":"https://PROVIDER_ONE/v1","model":"MODEL_ONE","key":"PROVIDER_ONE_KEY"},{"name":"backup","url":"https://PROVIDER_TWO/v1","model":"MODEL_TWO","key":"PROVIDER_TWO_KEY"}]'
ITACHI_TAVILY_KEY = "OPTIONAL_WEB_SEARCH_KEY"
# Or set ITACHI_HF_TOKEN = "YOUR_HUGGING_FACE_TOKEN" to discover eligible free chat models.
```

For a single provider, use `ITACHI_REASONING_URL`, `ITACHI_REASONING_MODEL` and `ITACHI_REASONING_KEY`. Up to five model routes are supported. Quota, timeout, context and selected server failures can trigger failover; invalid credentials do not. Each provider has its own rates and limits.

With `ITACHI_HF_TOKEN`, Itachi reads the provider's published model catalog at startup and admits only text chat models whose provider currently reports `live` and `is_free: true`. Availability and promotions can change. A Hugging Face token still has account-level credit and usage rules; Itachi cannot create the token or silently use your ChatGPT login. It discovers at most five models and never saves the token to the repository. Route selection estimates the question type, then uses session-only success and explicit helpfulness feedback to adjust ranking. It does **not** retrain or edit model weights.

With **no model route or token**, the hosted console still calculates arithmetic locally. If the internet checkbox is enabled it requests Wikipedia excerpts or public GitHub repository metadata, labels them as references, and cites URLs. It does not present those excerpts as a generated AI answer. The sidebar also offers a downloadable public source snapshot. For general reasoning and writing, add an authorized model in the private app's secrets. Search sends the question to the public API; do not include sensitive text. See [[Public_Learning_and_Recovery]].

## Autonomous research

The model chooses up to three read-only actions from `web_search`, `github_search`, `calculate` and `request_access`, then synthesizes an answer. `request_access` prepares a reviewable website proposal without contacting the site or registering an account. Internet search requires the web checkbox; Tavily is optional. The tools cannot edit files, run commands, access accounts or escalate privileges. See [[Autonomy_and_Permissions]].
