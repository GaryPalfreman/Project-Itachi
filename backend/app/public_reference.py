"""A small, labeled public-reference mode when no chat model is authorized."""
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote
import httpx
from .autonomy import calculate
from .account_requests import prepare as prepare_access


class _Plain(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


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


async def wikipedia(query: str) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get('https://en.wikipedia.org/w/rest.php/v1/search/page',
            params={'q':query[:200], 'limit':3},
            headers={'User-Agent':'ProjectItachi/0.2 (https://github.com/GaryPalfreman/Project-Itachi)'})
        response.raise_for_status()
    pages = response.json().get('pages', [])
    results = []
    for page in pages[:3] if isinstance(pages, list) else []:
        if not isinstance(page, dict) or not isinstance(page.get('key'), str):
            continue
        parser = _Plain()
        parser.feed(str(page.get('excerpt') or ''))
        excerpt = unescape(''.join(parser.parts))[:500]
        results.append({'title':str(page.get('title') or page['key'])[:160],
                        'url':'https://en.wikipedia.org/wiki/' + quote(page['key'][:200], safe=''),
                        'excerpt':excerpt})
    return results


async def reply(prompt: str, allow_web: bool) -> str:
    result = arithmetic(prompt)
    if result is not None:
        return 'Local calculation: ' + result
    if allow_web:
        try:
            pages = await wikipedia(prompt)
        except (httpx.HTTPError, ValueError):
            pages = []
        if pages:
            return ('Public reference results (article snippets; no AI answer model connected):\n\n' +
                    '\n\n'.join(f"**{p['title']}** — {p['url']}\n{p['excerpt']}" for p in pages))
        return 'Public reference search found no reliable match. A connected answer model is needed for this question.'
    try:
        if prompt.strip().startswith('https://'):
            return prepare_access(prompt.strip())
    except ValueError:
        pass
    return ('I can calculate locally. Enable public reference search for a source lookup. '
            'Generative answers require an authorized model route or Hugging Face token in app secrets.')
