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


def _wants_sources(prompt: str) -> bool:
    text = prompt.lower()
    return any(marker in text for marker in (
        'source', 'sources', 'citation', 'citations', 'reference', 'references',
        'link', 'links', 'url', 'urls', 'where did you get'
    ))


async def reply(prompt: str, allow_web: bool) -> str:
    result = arithmetic(prompt)
    if result is not None:
        return 'Local calculation: ' + result
    learned = search_learned(prompt, limit=4)
    if learned:
        return (
            'Itachi learned public references:\n\n'
            + learned_context(learned)
        )
    if allow_web:
        if task_for(prompt) == 'code' or any(word in prompt.lower() for word in ('repository', 'repositories', 'github')):
            try:
                repos = await search_repos(prompt)
            except (httpx.HTTPError, ValueError):
                repos = []
            if repos:
                if _wants_sources(prompt):
                    return ('Public GitHub repository references (metadata only; code not installed):\n\n' +
                            '\n\n'.join(f"**{r['name']}** — {r['url']}\n{r['description']} · License: {r['license']}"
                                        for r in repos))
                return '\n\n'.join(
                    f"**{r['name']}**\n{r['description']} · License: {r['license']}"
                    for r in repos
                )
        try:
            pages = await wikipedia(prompt)
        except (httpx.HTTPError, ValueError):
            pages = []
        if pages:
            if _wants_sources(prompt):
                return ('Public reference results:\n\n' +
                        '\n\n'.join(f"**{p['title']}** — {p['url']}\n{p['excerpt']}" for p in pages))
            return '\n\n'.join(str(p.get('excerpt') or '') for p in pages if p.get('excerpt'))
        return 'I found no reliable public-reference match for this request.'
    if any(word in prompt.lower() for word in ('repository', 'repositories', 'github')):
        repos = load_public_catalog().get('repositories', [])[:6]
        if repos:
            if _wants_sources(prompt):
                return ('Saved public repository catalog (metadata only; last refreshed on GitHub):\n\n' +
                        '\n\n'.join(f"**{r['name']}** — {r['url']}\n{r['description']} · License: {r['license']}"
                                    for r in repos))
            return '\n\n'.join(
                f"**{r['name']}**\n{r['description']} · License: {r['license']}"
                for r in repos
            )
    keywords = [word for word in prompt.lower().split() if len(word) > 4][:8]
    references = [r for r in load_public_catalog().get('references', [])[:8]
                  if any(word in (r.get('title', '') + ' ' + r.get('topic', '')).lower()
                         for word in keywords)][:3]
    if references:
        if _wants_sources(prompt):
            return ('Saved public reference excerpts:\n\n' +
                    '\n\n'.join(f"**{r['title']}** — {r['url']}\n{r['excerpt']}"
                                for r in references))
        return '\n\n'.join(str(r.get('excerpt') or '') for r in references if r.get('excerpt'))
    try:
        if prompt.strip().startswith('https://'):
            return prepare_access(prompt.strip())
    except ValueError:
        pass
    return ('I can calculate locally. Enable public reference search for a source lookup. '
            'Deeper generated answers are currently unavailable.')
