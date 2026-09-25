"""No-key public references, using Wikipedia's documented REST search."""
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote
import httpx


class _Plain(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


async def wikipedia(query: str) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get('https://en.wikipedia.org/w/rest.php/v1/search/page',
            params={'q':query[:200], 'limit':3},
            headers={'User-Agent':'ProjectItachi/0.3 (https://github.com/GaryPalfreman/Project-Itachi)'})
        response.raise_for_status()
    pages = response.json().get('pages', [])
    results = []
    for page in pages[:3] if isinstance(pages, list) else []:
        if not isinstance(page, dict) or not isinstance(page.get('key'), str):
            continue
        parser = _Plain()
        parser.feed(str(page.get('excerpt') or ''))
        results.append({'title':str(page.get('title') or page['key'])[:160],
                        'url':'https://en.wikipedia.org/wiki/' + quote(page['key'][:200], safe=''),
                        'excerpt':unescape(''.join(parser.parts))[:500]})
    return results
