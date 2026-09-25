"""Explicit, sourced web search. Only the query is sent to Tavily."""
import httpx

async def search(query: str, key: str, max_results: int = 4) -> list[dict[str, str]]:
    if not key:
        raise RuntimeError('Web search is not configured')
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post('https://api.tavily.com/search',
            headers={'Authorization': f'Bearer {key}'},
            json={'query': query[:500], 'search_depth': 'basic',
                  'max_results': max(1, min(max_results, 5)), 'include_answer': False})
        response.raise_for_status()
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
