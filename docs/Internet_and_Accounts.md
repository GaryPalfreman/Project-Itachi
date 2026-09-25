# Internet, Models and Account Boundaries

See [[Hosted_Testing]] for Streamlit secrets and [[Deployment_Mac]] for local Ollama and OpenClaw.

## What is wired now

| Capability | Itachi connection | Boundary |
| --- | --- | --- |
| Internet lookup | Opt-in Tavily API request from FastAPI or Streamlit | Only the question is sent for search; snippets are untrusted and URLs appear in responses. Requires `ITACHI_TAVILY_KEY`. |
| Local Ollama | OpenAI-compatible `http://127.0.0.1:11434/v1` | Works when Itachi runs on the Mac with Ollama; cloud hosts cannot reach Mac loopback. |
| Hosted Llama/Qwen/DeepSeek | Ordered compatible model routes in Streamlit secrets | Requires each provider's endpoint and key. Recoverable failures advance to another configured model, up to five. |
| OpenClaw | Optional, existing HTTP chat endpoint on Mac | Disabled in OpenClaw by default; operator gateway token must stay on the private local host. Existing gateway settings are not modified by Itachi. |
| Obsidian | Read-only local retrieval from `~/Documents/Engineering-Knowledge`; selected ZIP upload to Streamlit | The live vault stays on the Mac. Review every file and app visibility before uploading an export. |
| GitHub | Source repository and CI | There is no runtime GitHub write adapter or GitHub account token in the hosted app. |

ChatGPT's connected accounts (Google Drive, GitHub and other apps), GitKraken login, Codex session and Docker login are tied to their own authorization contexts. They do not automatically authorize a newly deployed Itachi server. Grant a specific connector its own narrowly scoped credential only after deciding its actions and storage rules. The Drive copy of Engineering-Knowledge is available for **development review** here; it is not automatically synchronized into a public app. MiroFish and JEV require a confirmed API contract before an adapter can run. ZIP Cloud likewise requires a documented API and independent authorization.

## Knowledge rules

The vault's provenance (`DOCUMENTED`, `OBSERVED`, `MEASURED`, `REPORTED`, `INFERRED`, `UNKNOWN`) and knowledge status (`RESEARCHED`, `VERIFIED`, `STANDARD-DEPENDENT`, `FIELD-VALIDATED`) are distinct. Retrieval should preserve source and authority; generated answers cannot promote status. Human review precedes any knowledge write. Keep PMES operational records in their source system; do not copy them into Itachi as an invented database.

## Model failover

Failover applies to 402, 408, 429, selected 5xx responses, transport errors and recognized context limit errors. It does not conceal invalid credentials (401/403) or unsupported model requests. A new provider receives the selected vault excerpts in its answer prompt, so choose routes appropriate for that data. Every provider has its own context, quota and cost limits; failover does not bypass them. A public cloud app cannot use an Ollama model running only on your Mac unless you set up an authenticated private network bridge.

## References

- [Tavily search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [OpenClaw HTTP chat endpoint](https://docs.openclaw.ai/gateway/openai-http-api)
