# Free Provider Assessment

This page records which public services can support [[Hosted_Testing]] without pretending that a browser chat is an API. Availability, free quotas and terms change; verify them at the provider before configuring a route. No personal information or credential is embedded in this repository.

## AI access

| Service | Current integration decision | What is required |
| --- | --- | --- |
| NVIDIA Nemotron | Supported as optional hosted OpenAI-compatible model route. | Create your own NVIDIA developer account and key, then put `ITACHI_NVIDIA_API_KEY` in **private Streamlit secrets**. Trial access and rate limits are provider controlled. |
| Hugging Face free inference models | Supported through live catalog discovery with a configured `ITACHI_HF_TOKEN`. | An account token and whatever free credits are currently offered; the app checks the published catalog for free live chat models. |
| Groq Qwen | Supported as optional hosted API route, currently `qwen/qwen3.8-27b`. | Groq account API key in `ITACHI_GROQ_API_KEY`; free-plan requests and tokens are rate limited. |
| OpenRouter free router | Supported as optional hosted API route, `openrouter/free`. | OpenRouter account API key in `ITACHI_OPENROUTER_API_KEY`; the selected model can change and free requests are limited. |
| Ollama (Llama, Qwen, DeepSeek, Nemotron variants) | Supported by the local backend as an OpenAI-compatible route. | A machine running Ollama and a pulled compatible model. A cloud Streamlit instance cannot reach your own `localhost`. |
| Duck.ai | Human-operated browser chat only; no automated route. | Its terms prohibit automated querying and building another AI service on it. |
| Perchance AI chat | Human-operated browser chat only; no automated route. | Its terms prohibit automated or nonhuman use. |
| AskAI.free | No no-cost API route. | Its published API requires a Pro/Max subscription after a payment; the free trial excludes API access. |
| PLAI.chat, Free Anonymous AI, ChatBot Chat App, similar browser chats | No verified supported programmatic API for these specific services. | Keep human browser use separate. An HTML page is not an authorized model endpoint. |

Free access is not unlimited access. A model route is used only when its provider has independently supplied a compatible API credential or local runtime. If every model route fails, Itachi returns a bounded public-reference result or an explicit error. It cannot obtain another service's model usage by silently scraping a chat interface.

## Storage and knowledge

| Service | Role | Activation |
| --- | --- | --- |
| This GitHub repository | Versioned **public** reference metadata and code; daily scheduled refresh, plus 30-day workflow artifact. | Configured in [[Public_Learning_and_Recovery]]; scheduled writes require repository Actions permissions and branch rules. |
| Zep Cloud | Optional future hosted memory, with a free prototype allowance currently advertised as 10,000 credits/month. | A real Zep account and API key, a scoped data policy, and an adapter. It is **not connected** or provisioned here. |
| Proton Drive | Optional personal cloud backup, currently advertises 5 GB free. Official CLI offers browser-assisted authentication and file upload. | The account owner must create and verify an account and authenticate the CLI. No headless CI backup is claimed here. |
| Google Drive | Optional backup with separate Google OAuth. | The owner must provide accurate signup details, complete any verification and set up OAuth. No account is created or connected here. |
| EXPERTE.com free cloud storage page | Comparison and research article. | There is no EXPERTE storage account to create from that article. Choose an actual storage provider instead. |
| Optional HTTPS mirrors | Up to three user-authorized object storage endpoints for the public JSON catalog. | Supply each provider's HTTPS object URL and dedicated token as repository secrets per [[Public_Learning_and_Recovery]]. |

None of the services listed above has a general account token that Itachi can issue to itself. Account creation may require service-specific terms, a password, CAPTCHA, human verification or truthful personal details. Do not submit invented identity data or place credentials in the public repository. Cloud storage for the public snapshot does not automatically give the application permission to upload a private Obsidian vault. See [[Internet_and_Accounts]].

## Provider documentation

- [NVIDIA Nemotron developer endpoint](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b)
- [Groq OpenAI-compatible endpoint](https://console.groq.com/docs/openai) and [free-plan limits](https://console.groq.com/docs/rate-limits)
- [OpenRouter free-model router](https://openrouter.ai/docs/guides/routing/routers/free-router) and [free-model limits](https://openrouter.ai/docs/faq)
- [Duck.ai terms](https://duckduckgo.com/duckai/terms)
- [Perchance terms](https://perchance.org/terms-of-service)
- [AskAI.free API](https://askai.free/api)
- [Zep pricing](https://www.getzep.com/pricing/)
- [Proton Drive free storage](https://proton.me/drive/pricing)
- [Proton Drive CLI](https://proton.me/support/drive-cli)
- [Google account signup](https://support.google.com/accounts/answer/27441)
