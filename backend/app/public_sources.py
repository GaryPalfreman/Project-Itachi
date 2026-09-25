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
    headers = {'User-Agent':'ProjectItachi/0.4 (https://github.com/GaryPalfreman/Project-Itachi)'}
    async with httpx.AsyncClient(timeout=12, headers=headers) as client:
        response = await client.get(
            'https://en.wikipedia.org/w/rest.php/v1/search/page',
            params={'q':query[:200], 'limit':4},
        )
        response.raise_for_status()
        pages = response.json().get('pages', [])
        selected = [
            page for page in (pages[:4] if isinstance(pages, list) else [])
            if isinstance(page, dict) and isinstance(page.get('key'), str)
        ]
        if not selected:
            return []

        titles = '|'.join(page['key'][:200] for page in selected)
        extract_response = await client.get(
            'https://en.wikipedia.org/w/api.php',
            params={
                'action':'query',
                'prop':'extracts',
                'exintro':'1',
                'explaintext':'1',
                'redirects':'1',
                'titles':titles,
                'format':'json',
                'formatversion':'2',
            },
        )
        extract_response.raise_for_status()
        extract_pages = extract_response.json().get('query', {}).get('pages', [])
        extracts = {}
        if isinstance(extract_pages, list):
            for item in extract_pages:
                if not isinstance(item, dict):
                    continue
                title = str(item.get('title') or '')
                text = str(item.get('extract') or '')
                if title and text:
                    extracts[title.casefold()] = text

    results = []
    for page in selected:
        parser = _Plain()
        parser.feed(str(page.get('excerpt') or ''))
        title = str(page.get('title') or page['key'])[:160]
        search_excerpt = unescape(''.join(parser.parts))
        full_excerpt = extracts.get(title.casefold(), '')
        excerpt = (full_excerpt or search_excerpt)[:1400]
        results.append({
            'title': title,
            'url':'https://en.wikipedia.org/wiki/' + quote(page['key'][:200], safe=''),
            'excerpt': excerpt,
        })
    return results
