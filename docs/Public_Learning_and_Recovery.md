# Public Learning and Recovery

Itachi grows a **public reference catalog**, not its model weights. No personal vault, user conversation, secret, executable repository code or scraped login-only page is collected. See [[Autonomy_and_Permissions]] and [[Hosted_Testing]].

## What runs without a personal token

The hosted app can retrieve public Wikipedia excerpts and public GitHub repository metadata after the visitor enables internet lookup. The autonomous planner can use `web_search` (Wikipedia when no Tavily key), `github_search`, arithmetic and access-request proposals. Public references are cited, treated as untrusted, and never run as instructions. GitHub repository search fetches metadata and license identifiers only; it does not clone, install or execute third-party projects. Public GitHub REST access is rate limited, especially from a shared cloud IP.

On a daily schedule, `.github/workflows/refresh-public.yml` reads the allowlists in `sources/public_repos.json` and `sources/public_topics.json`. It saves a compact JSON snapshot to `data/public_catalog.json` and keeps a 30-day workflow artifact. The snapshot ships with the application and can be downloaded from the Streamlit sidebar; after a restart the checked-in copy is present again. The workflow's automatically issued `GITHUB_TOKEN` is scoped to this repository and expires; it is not an independent AI account or a credential for writing to arbitrary cloud services. Schedule runs can be delayed, and pushing the refreshed file requires the repository's Actions settings and branch rules to permit it.

To refresh manually from the GitHub Actions page, choose **Refresh public catalog → Run workflow**, or run locally from the project root:

```bash
python -m pip install -r backend/requirements.txt
python -m scripts.refresh_public_catalog
```

The script will leave the previous snapshot intact if no allowlisted repository is reachable. Review source names, licenses and actual documentation before making any source part of Itachi's runtime dependencies. To add a source, edit the allowlists and review the resulting diff; fetched descriptions and excerpts do not gain authority just by being stored.

## Optional other cloud storage

Up to three independently authorized HTTPS object endpoints can receive the **public catalog only** through `backend/app/mirrors.py`. They must support authenticated HTTP `PUT` with a bearer token. Set GitHub Actions repository secrets such as:

```text
ITACHI_MIRRORS_JSON=[{"name":"backup_one","url":"https://YOUR_STORAGE_HOST/path/catalog.json","token_env":"ITACHI_MIRROR_TOKEN_1"}]
ITACHI_MIRROR_TOKEN_1=YOUR_STORAGE_SERVICE_TOKEN
```

These examples are placeholders. No secondary service or token is present now. Free tiers and account requirements depend on the chosen provider. Presigned URLs containing query credentials and internal network targets are rejected. Each mirror must be authorized by its own service; a GitHub token cannot write to that service. Optional mirror failures are visible in workflow logs and do not remove the GitHub snapshot.

## Multiple AI models

When independently authorized routes are configured, Itachi ranks them by task and temporary reliability data, then fails over on recoverable errors. Hugging Face free-model discovery requires an account token supplied in private app secrets. Public Wikipedia and GitHub APIs supply **references**, not a general language model. Itachi cannot issue itself an AI provider token without an account or guarantee unlimited free inference. See [[Hosted_Testing]].

See [[Free_Provider_Assessment]] for a verified distinction between supported API routes, browser-only chat products and optional storage services.

## Primary references

- [GitHub Actions workflow schedules and permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [GitHub REST API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [MediaWiki REST API search](https://www.mediawiki.org/wiki/API:REST_API/Reference#Search_pages)
