"""Explicit, sourced web search. Only the query is sent to Tavily."""
import time
import httpx

from .runtime_health import available, record_failure, record_success

async def search(query: str, key: str, max_results: int = 4) -> list[dict[str, str]]:
    if not key:
        raise RuntimeError('Web search is not configured')
    health_key = 'external:web-search'
    if not available(health_key):
        raise RuntimeError('Web search is temporarily cooling down')
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post('https://api.tavily.com/search',
                headers={'Authorization': f'Bearer {key}'},
                json={'query': query[:500], 'search_depth': 'basic',
                      'max_results': max(1, min(max_results, 5)), 'include_answer': False})
            response.raise_for_status()
        record_success(health_key, (time.perf_counter() - started) * 1000.0)
    except Exception as error:
        record_failure(health_key, error)
        raise
    results = []
    for item in response.json().get('results', []):
        if not isinstance(item, dict):
            continue
        url = str(item.get('url', ''))
        if not url.startswith(('https://', 'http://')):
            continue
        results.append({'title': str(item.get('title', ''))[:200],
                        'url': url[:1500], 'excerpt': str(item.get('content', ''))[:900]})
    return results

def context(results: list[dict[str, str]]) -> str:
    return '\n\n'.join(f"[Web {i}] {r['title']} | {r['url']}\n{r['excerpt']}"
                     for i, r in enumerate(results, 1))[:5000]
