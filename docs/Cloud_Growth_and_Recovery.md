# Cloud Growth and Recovery

Itachi is designed to keep working without a personal computer or a single AI provider.

## Durable layers

1. **GitHub repository and history** are the primary recovery source. Public-learning snapshots are committed to `data/knowledge/`.
2. **GitHub Actions** issues an ephemeral `GITHUB_TOKEN` to each workflow run. It is not a personal access token and is used only for public GitHub discovery/metadata.
3. **Supabase** is an optional second durable copy of the public knowledge corpus. A server-side key is stored only in GitHub Actions secrets; public Streamlit users never receive it.
4. **Zep Cloud** can optionally receive a throttled subset of newly learned public facts as a tertiary graph-memory layer; duplicate hashes and a six-hour ingestion throttle protect its free allowance.
5. **Google Drive** can mirror recovery snapshots through a dedicated Itachi Google account and OAuth grant.
6. **MEGA** can mirror the same recovery tree to a dedicated encrypted storage account.
7. **GitHub Actions artifacts** retain rolling recovery snapshots.
8. **Optional HTTPS mirrors** can receive the already-public catalog through dedicated mirror credentials.

The system never needs `127.0.0.1` for its hosted learning path.

## Continuous public learning

The workflow in `.github/workflows/refresh-public.yml` runs after main-branch deployments and hourly. It:

- refreshes allowlisted public GitHub repository metadata;
- discovers high-quality public repositories for configured engineering/AI topics;
- reads short README excerpts only from permissively licensed repositories;
- ingests short attributed Wikipedia excerpts;
- ingests configured RSS/Atom feed excerpts;
- stores source URL, license, timestamp, and content hash with every record;
- never runs, installs, imports, or executes code taken from discovered repositories;
- bounds the corpus so free-tier storage cannot grow without limit;
- replicates the public corpus to Supabase when configured;
- keeps a GitHub Actions recovery artifact.

This is learning by retrieval and knowledge growth, not autonomous weight training or self-modifying code.

## AI provider pool

Itachi's model router can fail over across separately authorized providers. Supported server-side routes include:

- TypeSafe JEV for typed routing/relevance decisions (not prose generation);
- NVIDIA hosted Nemotron;
- Groq free-plan models;
- Google Gemini API free-tier models;
- Cerebras Inference;
- Hugging Face Inference Providers;
- OpenRouter routes;
- any administrator-supplied OpenAI-compatible endpoint in `ITACHI_MODEL_ROUTES_JSON`.

Provider credentials remain server-side. Users of the Streamlit application do not need their own model accounts.

## Browser-only free AI sites

Itachi must not automate services that do not offer a supported developer API or whose terms prohibit automated querying. Browser-only sites can still be used manually by a person, but they are not backend dependencies.

Duck.ai is intentionally excluded from automated routing because its Terms prohibit automated querying and developing/offering AI services through Duck.ai. AskAI.free is not a free API: API keys require a paid Pro or Max subscription. Other anonymous browser chat sites are excluded until they publish a stable developer API and automation terms that permit this use.

This avoids building Itachi around brittle scraping, CAPTCHAs, session cookies, or undocumented endpoints.

## Supabase setup

Apply `supabase/migrations/20260925103000_itachi_public_knowledge.sql` to the dedicated Itachi Supabase project.

Set these GitHub Actions repository secrets:

```
ITACHI_SUPABASE_URL
ITACHI_SUPABASE_SERVER_KEY
```

The hourly workflow will then upsert the public corpus to Supabase and also try to keep a Storage snapshot in the `itachi-recovery` bucket.

The manual `Recover Itachi public knowledge` GitHub Action can rebuild the repository snapshot from Supabase.

## User privacy

Public web knowledge can be shared globally. User conversations are different: they stay session-scoped unless an explicit authenticated memory design is added later. Itachi does not silently merge every visitor's chat into one global memory pool.


## Zep optional graph replica

Zep is not the primary store. If you create a dedicated free Zep project and add its key to the repository secret `ITACHI_ZEP_API_KEY`, the hourly workflow checks whether six hours have elapsed and sends at most three unseen public records. This prevents duplicate ingestion and keeps usage well below the free-tier design target under normal operation.

Zep credentials are never committed to GitHub or exposed to Streamlit users.


Google Drive and MEGA setup and recovery are documented in [[Google_Drive_and_MEGA]].


JEV routing details are documented in [[JEV_Decision_Layer]].
