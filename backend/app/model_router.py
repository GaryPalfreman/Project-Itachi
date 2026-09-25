"""Bounded model failover for compatible chat-completion endpoints."""
import time
import httpx

from .runtime_health import available, record_failure, record_success, snapshot

CONTEXT_MARKERS = ('context length', 'context window', 'maximum context',
                   'too many tokens', 'token limit', 'prompt is too long')
ROUTE_MARKERS = ('model not found', 'unknown model', 'unsupported model',
                 'invalid model', 'does not exist', 'not available')

def may_fallback(error: Exception) -> bool:
    if isinstance(error, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        code = error.response.status_code
        if code in {401, 402, 403, 404, 408, 429, 500, 502, 503, 504}:
            return True
        if code == 400:
            text = error.response.text.lower()
            return any(term in text for term in CONTEXT_MARKERS + ROUTE_MARKERS)
    return False

async def completion(url: str, model: str, key: str, messages: list[dict]) -> str:
    if not url or not model:
        raise RuntimeError('Selected model endpoint is not configured')
    headers = {'Authorization': f'Bearer {key}'} if key else {}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url.rstrip('/') + '/chat/completions',
            headers=headers, json={'model': model, 'messages': messages, 'stream': False})
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        if not isinstance(content, str):
            raise RuntimeError('Model returned an unsupported response format')
        return content

async def with_fallback(primary: tuple[str, str, str], fallback: tuple[str, str, str],
                        messages: list[dict]) -> tuple[str, str]:
    """Return answer and route name; never retry endlessly or hide auth errors."""
    try:
        return await completion(*primary, messages), 'primary'
    except Exception as first:
        if not fallback[0] or not fallback[1] or not may_fallback(first):
            raise
        try:
            return await completion(*fallback, messages), 'fallback'
        except Exception as second:
            raise RuntimeError(f'Primary and fallback unavailable ({type(first).__name__}; '
                               f'{type(second).__name__})') from second

async def cascade(routes: list, messages: list[dict]) -> tuple[str, str]:
    """Try healthy configured routes and quarantine failing routes for bounded cooldowns."""
    if not routes:
        raise RuntimeError('No model routes configured')

    candidates = [
        route for route in routes
        if available(f"model:{route.name}")
    ]
    if not candidates:
        candidates = list(routes)

    last = None
    attempted = 0
    for route in candidates:
        attempted += 1
        health_key = f"model:{route.name}"
        started = time.perf_counter()
        try:
            answer = await completion(route.url, route.model, route.key, messages)
            record_success(health_key, (time.perf_counter() - started) * 1000.0)
            return answer, route.name
        except Exception as error:
            last = error
            record_failure(health_key, error)
            if not may_fallback(error):
                break

    if last is None:
        raise RuntimeError('No healthy model routes available')
    if attempted > 1 and may_fallback(last):
        raise RuntimeError(f'All healthy model routes unavailable ({type(last).__name__})') from last
    raise last


def route_health(name: str) -> dict:
    """Expose non-secret runtime reliability/latency for ranking."""
    return snapshot(f"model:{name}")
