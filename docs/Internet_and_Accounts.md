# Internet and Account Boundaries

See [[Autonomy_and_Permissions]], [[Hosted_Testing]] and [[Deployment_Mac]].

| Capability | Connection | Access |
| --- | --- | --- |
| Web search | Tavily API | Per-question internet checkbox, server-side key; sends derived search query and returns cited URLs. |
| Models | Ordered OpenAI-compatible routes | Up to five separately configured providers, including local Ollama when running on the same machine. |
| Arithmetic | Local restricted parser | Numeric expressions only, no shell or Python evaluation. |
| OpenClaw / JEV | Optional existing adapters | Separately configured endpoints; autonomous research does not require either. |
| Knowledge and accounts | Disabled by default | No local personal vault scan, hosted note import or inherited ChatGPT connector credentials. |

ChatGPT connector authorizations, GitKraken login, Codex sessions and Docker login do not transfer to a deployed app. Each future integration needs a specific API, its own authorization and an action policy. Credentials stay server-side. No confirmation phrase can override an account's or provider's access policies.

Failover handles selected quota, availability and context failures. It cannot bypass quota limits, and it does not hide invalid credentials. Providers receive the current question and tool findings; do not send sensitive text to a provider you have not approved.
