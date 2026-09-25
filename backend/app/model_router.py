"""Bounded model failover for compatible chat-completion endpoints."""
import httpx

CONTEXT_MARKERS = ('context length', 'context window', 'maximum context',
                   'too many tokens', 'token limit', 'prompt is too long')

def may_fallback(error: Exception) -> bool:
    if isinstance(error, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        code = error.response.status_code
        if code in {402, 408, 429, 500, 502, 503, 504}:
            return True
        if code == 400:
            return any(term in error.response.text.lower() for term in CONTEXT_MARKERS)
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
