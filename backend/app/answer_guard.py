"""Guaranteed Itachi answer path with bounded autonomous and fallback stages."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .autonomy import run as autonomous_run
from .model_router import cascade
from .public_reference import reply as reference_reply
from .web_search import search, context as web_context
from .rapidapi_tools import web_search as rapid_web_search


def _text(value: object) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _timeout_for(depth: str) -> int:
    depth = depth.lower().strip() if isinstance(depth, str) else 'auto'
    if depth == 'deep':
        return 110
    if depth == 'quick':
        return 45
    return 70


async def guaranteed_answer(
    prompt: str,
    routes: list,
    web_key: str = '',
    allow_web: bool = True,
    depth: str = 'auto',
    extra_context: str = '',
    rapidapi_key: str = '',
) -> tuple[str, str]:
    """Return non-empty answer text and the internal route used when available."""
    autonomous_error = None
    try:
        result = await asyncio.wait_for(
            autonomous_run(
                prompt,
                routes,
                web_key,
                allow_web,
                depth=depth,
                return_route=True,
                extra_context=extra_context,
                rapidapi_key=rapidapi_key,
            ),
            timeout=_timeout_for(depth),
        )
        if isinstance(result, tuple):
            answer = _text(result[0])
            route = _text(result[1])
        else:
            answer = _text(result)
            route = ''
        if answer:
            return answer, route
    except Exception as error:
        autonomous_error = error

    current_date = datetime.now(timezone.utc).date().isoformat()
    fresh_results = []
    if allow_web and web_key:
        try:
            fresh_results = await asyncio.wait_for(search(prompt, web_key), timeout=15)
        except Exception:
            fresh_results = []
    if allow_web and not fresh_results and rapidapi_key:
        try:
            fresh_results = await asyncio.wait_for(
                rapid_web_search(prompt, rapidapi_key),
                timeout=15,
            )
        except Exception:
            fresh_results = []

    if routes:
        evidence = web_context(fresh_results) if fresh_results else '(fresh web search unavailable)'
        messages = [
            {
                'role': 'system',
                'content': (
                    'You are Itachi. Give a direct, useful answer. Current date: '
                    + current_date
                    + '. Use fresh evidence when supplied, prefer current authoritative facts, '
                      'and never expose internal provider/model names. If evidence is uncertain, say so.'
                ),
            },
            {
                'role': 'user',
                'content': (
                    f'Question:\n{prompt}\n\n'
                    f'Fresh web evidence:\n{evidence}\n\n'
                    f'Additional context (may be stale):\n{extra_context or "(none)"}'
                ),
            },
        ]
        try:
            answer, route = await asyncio.wait_for(cascade(routes, messages), timeout=45)
            answer = _text(answer)
            if answer:
                if fresh_results and 'Web sources:' not in answer:
                    urls = [str(item.get('url') or '') for item in fresh_results if isinstance(item, dict)]
                    urls = [url for url in urls if url]
                    if urls:
                        answer += '\n\nWeb sources: ' + ', '.join(dict.fromkeys(urls))
                return answer, _text(route)
        except Exception:
            pass

    try:
        fallback = await asyncio.wait_for(reference_reply(prompt, bool(allow_web)), timeout=20)
        fallback = _text(fallback)
        if fallback:
            return fallback, ''
    except Exception:
        pass

    reason = type(autonomous_error).__name__ if autonomous_error is not None else 'Unavailable'
    return (
        f'I could not complete the full answer pipeline just now ({reason}). '
        'Please ask me again; I am still online.',
        '',
    )
