# Autonomy and Permissions

Itachi plans up to three read-only actions per question and answers through an ordered model chain. Current actions are sourced web search, bounded arithmetic and account-access proposals. The local Face offers an **Autonomous** route; Streamlit offers an **Autonomous research** checkbox. Web search needs the separate per-question toggle. See [[Hosted_Testing]] and [[Protocol_and_State_Rules]].

No personal data is preloaded. Local vault lookup and note endpoints return no content unless `ITACHI_ENABLE_KNOWLEDGE=true` is explicitly configured; the default path is a bundled sample. The hosted console has no note upload interface. Research and calculation do not require OpenClaw. The underlying model name remains visible in answers for auditability.

## Model choice and improvement

Itachi ranks configured models for code, reasoning, research and general prompts. In the hosted console, only route success counts and optional “Helpful / Needs work” votes are kept in the visitor's temporary session; question text is not stored in the routing feedback. Itachi can discover eligible Hugging Face chat models when its operator provides `ITACHI_HF_TOKEN`. It cannot mint account tokens, install an unrestricted cloud model, rewrite its own source or train itself from user chats. See [[Hosted_Testing]] for exact secrets and the no-model reference mode.

The requested confirmation phrase is **not stored or recognized** as a bypass key. A phrase entered into a chat cannot grant authority over third-party accounts, provider quotas, safety requirements or remote machines. A future permission request should name the exact action, destination and data, then use service-native authentication and action-specific approval. If a tool is unavailable, Itachi reports that instead of pretending to have completed it.

## Account access proposals

The planner can propose a public HTTPS website home URL. Itachi validates the URL locally and appends a pending access request to the answer. It **does not** create an account, contact the site, make an email address, accept terms, pay, store passwords or solve a CAPTCHA. A CAPTCHA is a website's verification step; a person may need to complete it directly. Account creation depends on the site's rules, identity requirements and a specific authorized integration. No generic automated signup is enabled.

To add a capability, implement a narrow tool adapter, validate its inputs, establish an authorization scope and decide which actions may run unattended. Keep write or external actions behind an explicit authorization policy. Test the adapter before adding it to the planner's allowlist.
