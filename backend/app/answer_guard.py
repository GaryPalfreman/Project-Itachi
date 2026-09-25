"""Guaranteed Itachi answer path with bounded autonomous and fallback stages."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .autonomy import run as autonomous_run, is_control_payload
from .model_router import cascade
from .public_reference import reply as reference_reply
from .web_search import search, context as web_context
from .rapidapi_tools import web_search as rapid_web_search


def _wants_sources(prompt: str) -> bool:
    text = prompt.lower()
    return any(marker in text for marker in (
        'source', 'sources', 'citation', 'citations', 'reference', 'references',
        'link', 'links', 'url', 'urls', 'where did you get'
    ))


def _strip_source_footer(answer: str) -> str:
    """Remove common provider/source footers from ordinary Itachi replies."""
    text = str(answer or '').strip()
    markers = (
        '\n\nWeb sources:',
        '\n\nSources:',
        '\n\nSource:',
        '\nWeb sources:',
        '\nSources:',
        '\nSource:',
    )
    cut = len(text)
    for marker in markers:
        index = text.find(marker)
        if index >= 0:
            cut = min(cut, index)
    return text[:cut].rstrip()


def _final_answer(prompt: str, value: object) -> str:
    """Validate and clean a candidate answer before it can reach the UI."""
    answer = _text(value)
    if not answer or is_control_payload(answer):
        return ''
    return answer if _wants_sources(prompt) else _strip_source_footer(answer)


def _text(value: object) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _timeout_for(depth: str) -> int:
    depth = depth.lower().strip() if isinstance(depth, str) else 'auto'
    if depth == 'deep':
        return 52
    if depth == 'quick':
        return 35
    # Vercel's function has a 60-second ceiling.  Reserve time for response delivery.
    return 52


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
    deadline = _timeout_for(depth)
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
            timeout=deadline,
        )
        if isinstance(result, tuple):
            answer = _text(result[0])
            route = _text(result[1])
        else:
            answer = _text(result)
            route = ''
        answer = _final_answer(prompt, answer)
        if answer:
            return answer, route
        autonomous_error = RuntimeError('Autonomous answer was internal tool-control data')
    except Exception as error:
        autonomous_error = error

    current_date = datetime.now(timezone.utc).date().isoformat()
    fresh_results = []
    # The autonomous pass owns most of the deadline.  Keep recovery bounded so a
    # serverless invocation can always return a useful response before Vercel ends it.
    recovery_timeout = 10
    if allow_web and web_key:
        try:
            fresh_results = await asyncio.wait_for(search(prompt, web_key), timeout=recovery_timeout)
        except Exception:
            fresh_results = []
    if allow_web and not fresh_results and rapidapi_key:
        try:
            fresh_results = await asyncio.wait_for(
                rapid_web_search(prompt, rapidapi_key),
                timeout=recovery_timeout,
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
                      'and never expose internal provider/model names, API names, source names, citations, '
                      'or URLs unless the user explicitly asks for sources. If evidence is uncertain, say so.'
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
            answer, route = await asyncio.wait_for(cascade(routes, messages), timeout=20)
            cleaned = _final_answer(prompt, answer)
            if cleaned:
                return cleaned, _text(route)

            retry_messages = [
                {
                    'role': 'system',
                    'content': (
                        'You are Itachi. Research is already complete. Return the final user-facing '
                        'prose answer only. Do not request, call, describe, or output tools, functions, '
                        'actions, planner JSON, or tool-call JSON. '
                        + ('Include concise source links because the user explicitly requested sources.'
                           if _wants_sources(prompt)
                           else 'Do not include source/provider/API names or URLs.')
                    ),
                },
                {
                    'role': 'user',
                    'content': (
                        f'Question:\n{prompt}\n\n'
                        f'Fresh web evidence:\n{evidence}\n\n'
                        f'Additional context:\n{extra_context or "(none)"}'
                    ),
                },
            ]
            answer, route = await asyncio.wait_for(cascade(routes, retry_messages), timeout=15)
            cleaned = _final_answer(prompt, answer)
            if cleaned:
                return cleaned, _text(route)
        except Exception:
            pass

    try:
        fallback = await asyncio.wait_for(reference_reply(prompt, bool(allow_web)), timeout=10)
        fallback = _final_answer(prompt, fallback)
        if fallback:
            return fallback, ''
    except Exception:
        pass

    if any(marker in prompt.lower() for marker in ('trading at', 'stock price', 'share price', 'market price', 'ticker')):
        return ('The live market lookup is temporarily unavailable. Please try again shortly.', '')
    reason = type(autonomous_error).__name__ if autonomous_error is not None else 'Unavailable'
    return (
        f'I could not complete the full answer pipeline just now ({reason}). '
        'Please ask me again; I am still online.',
        '',
    )
