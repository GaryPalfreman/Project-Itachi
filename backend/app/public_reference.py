"""A small, labeled public-reference mode when no chat model is authorized."""
import httpx
from .autonomy import calculate
from .account_requests import prepare as prepare_access
from .public_sources import wikipedia
from .github_public import search_repos
from .model_selection import task_for
from .public_catalog import load as load_public_catalog
from .public_knowledge import search as search_learned, context as learned_context


def arithmetic(prompt: str) -> str | None:
    text = prompt.strip().rstrip('? .')
    for prefix in ('what is ', 'calculate ', 'compute ', 'solve '):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.replace('×', '*').replace('÷', '/')
    if not text or not all(c in '0123456789.+-*/()% ' for c in text):
        return None
    try:
        return f'{text} = {calculate(text)}'
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None


async def reply(prompt: str, allow_web: bool) -> str:
    result = arithmetic(prompt)
    if result is not None:
        return 'Local calculation: ' + result
    learned = search_learned(prompt, limit=4)
    if learned:
        return (
            'Itachi learned public references (source excerpts; no generative model required):\n\n'
            + learned_context(learned)
        )
    if allow_web:
        if task_for(prompt) == 'code' or any(word in prompt.lower() for word in ('repository', 'repositories', 'github')):
            try:
                repos = await search_repos(prompt)
            except (httpx.HTTPError, ValueError):
                repos = []
            if repos:
                return ('Public GitHub repository references (metadata only; code not installed):\n\n' +
                        '\n\n'.join(f"**{r['name']}** — {r['url']}\n{r['description']} · License: {r['license']}"
                                    for r in repos))
        try:
            pages = await wikipedia(prompt)
        except (httpx.HTTPError, ValueError):
            pages = []
        if pages:
            return ('Public reference results (article snippets; no AI answer model connected):\n\n' +
                    '\n\n'.join(f"**{p['title']}** — {p['url']}\n{p['excerpt']}" for p in pages))
        return 'Public reference search found no reliable match. A connected answer model is needed for this question.'
    if any(word in prompt.lower() for word in ('repository', 'repositories', 'github')):
        repos = load_public_catalog().get('repositories', [])[:6]
        if repos:
            return ('Saved public repository catalog (metadata only; last refreshed on GitHub):\n\n' +
                    '\n\n'.join(f"**{r['name']}** — {r['url']}\n{r['description']} · License: {r['license']}"
                                for r in repos))
    keywords = [word for word in prompt.lower().split() if len(word) > 4][:8]
    references = [r for r in load_public_catalog().get('references', [])[:8]
                  if any(word in (r.get('title', '') + ' ' + r.get('topic', '')).lower()
                         for word in keywords)][:3]
    if references:
        return ('Saved public reference excerpts (not an AI-generated answer):\n\n' +
                '\n\n'.join(f"**{r['title']}** — {r['url']}\n{r['excerpt']}"
                            for r in references))
    try:
        if prompt.strip().startswith('https://'):
            return prepare_access(prompt.strip())
    except ValueError:
        pass
    return ('I can calculate locally. Enable public reference search for a source lookup. '
            'Generative answers require an authorized model route or Hugging Face token in app secrets.')
