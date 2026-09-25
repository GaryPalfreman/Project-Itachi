"""TypeSafe Jev System One decision layer for Itachi.

Jev is not a chat model. It returns typed decisions used to route work, gate
optional web lookup, and decide whether stored public knowledge is likely useful.
Credentials are server-side only.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

import httpx

from .runtime_health import available, record_failure, record_success

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"
TASKS = {"general", "code", "research", "reasoning"}


@dataclass(frozen=True)
class JevDecision:
    task: str = "general"
    needs_web: bool = False
    use_learned_knowledge: bool = True
    web_probability: float = 0.0
    knowledge_probability: float = 1.0


def _probability(answer: object, field: str, default: float) -> float:
    if not isinstance(answer, dict):
        return default
    value = answer.get(field)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def parse_decision(payload: dict) -> JevDecision:
    answers = payload.get("answers", {}) if isinstance(payload, dict) else {}
    if not isinstance(answers, dict):
        answers = {}

    route = answers.get("route", {})
    task = route.get("choice") if isinstance(route, dict) else None
    if not isinstance(task, str) or task not in TASKS:
        task = "general"

    web_probability = _probability(answers.get("needs_web"), "noul", 0.0)
    knowledge_probability = _probability(
        answers.get("use_learned_knowledge"), "noul", 1.0
    )
    return JevDecision(
        task=task,
        needs_web=web_probability >= 0.55,
        use_learned_knowledge=knowledge_probability >= 0.40,
        web_probability=web_probability,
        knowledge_probability=knowledge_probability,
    )


async def evaluate_prompt(
    prompt: str,
    api_key: str,
    *,
    url: str = JEV_URL,
    timeout: float = 8.0,
) -> JevDecision:
    """Return typed routing decisions. Failures should be handled by the caller."""
    if not api_key:
        raise ValueError("TYPESAFE_API_KEY is required")
    if not prompt.strip():
        raise ValueError("prompt must not be empty")

    body = {
        "model": JEV_MODEL,
        "state": {"user_request": prompt[:12000]},
        "questions": {
            "route": {
                "type": "choice",
                "instructions": (
                    "Choose the primary task type that should determine which "
                    "AI provider Itachi tries first."
                ),
                "criteria": {
                    "general": "General writing, conversation, or broad assistance",
                    "code": "Programming, debugging, APIs, software or code generation",
                    "research": "Current facts, source checking, news, comparison or web research",
                    "reasoning": "Math, logic, analysis, planning or multi-step reasoning",
                },
            },
            "needs_web": {
                "type": "noul",
                "instructions": (
                    "Would answering this request accurately benefit materially "
                    "from fresh external web information?"
                ),
            },
            "use_learned_knowledge": {
                "type": "noul",
                "instructions": (
                    "Is a previously collected public engineering and AI knowledge "
                    "corpus likely to help answer this request?"
                ),
            },
        },
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    health_key = "external:decision-layer"
    if not available(health_key):
        raise RuntimeError("Decision layer is temporarily cooling down")
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()
        record_success(health_key, (time.perf_counter() - started) * 1000.0)
        return parse_decision(payload)
    except Exception as error:
        record_failure(health_key, error)
        raise
