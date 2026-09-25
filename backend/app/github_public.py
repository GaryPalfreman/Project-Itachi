"""Bounded read-only discovery of public GitHub repository metadata."""
import re
import httpx

API = 'https://api.github.com'
AGENT = 'ProjectItachi/0.3 (https://github.com/GaryPalfreman/Project-Itachi)'
NAME = re.compile(r'^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$')


def normalize(item: dict) -> dict[str, str | int] | None:
    full_name = item.get('full_name', '') if isinstance(item, dict) else ''
    if not isinstance(full_name, str) or not NAME.fullmatch(full_name):
        return None
    license_data = item.get('license') or {}
    return {'name':full_name, 'url':'https://github.com/' + full_name,
            'description':str(item.get('description') or '')[:300],
            'license':str(license_data.get('spdx_id') or 'UNKNOWN')[:60],
            'stars':int(item.get('stargazers_count') or 0),
            'updated':str(item.get('pushed_at') or '')[:40]}


async def search_repos(query: str, limit: int = 3) -> list[dict]:
    """Search metadata only; never clone, run or install repository code."""
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(API + '/search/repositories',
            params={'q':query[:100] + ' archived:false fork:false',
                    'sort':'stars', 'order':'desc', 'per_page':max(1, min(limit, 5))},
            headers={'Accept':'application/vnd.github+json', 'User-Agent':AGENT})
        response.raise_for_status()
    return [repo for item in response.json().get('items', [])[:5]
            if (repo := normalize(item)) is not None][:limit]


async def catalog_repos(names: list[str], token: str = '') -> list[dict]:
    """Fetch only explicit allowlisted repository names."""
    headers = {'Accept':'application/vnd.github+json', 'User-Agent':AGENT}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    results = []
    async with httpx.AsyncClient(timeout=12, headers=headers) as client:
        for name in names[:8]:
            if not isinstance(name, str) or not NAME.fullmatch(name):
                continue
            try:
                response = await client.get(API + '/repos/' + name)
                response.raise_for_status()
                item = normalize(response.json())
                if item and item['name'].casefold() == name.casefold():
                    results.append(item)
            except (httpx.HTTPError, ValueError):
                continue
    return results
