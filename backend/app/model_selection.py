"""Task-aware routing with session-only provider reliability feedback."""
import re
import httpx
from .model_catalog import ModelRoute
from .model_router import route_health

HF_BASE = 'https://router.huggingface.co/v1'


def task_for(prompt: str) -> str:
    text = prompt.lower()
    if re.search(r'\b(python|javascript|typescript|code|program|debug|stack trace|function|script|api)\b', text):
        return 'code'
    if re.search(r'\b(latest|today|recent|source|research|compare|news|current)\b', text):
        return 'research'
    if re.search(r'\b(calculate|solve|equation|proof|derive|logic|reasoning)\b', text):
        return 'reasoning'
    return 'general'


def rank(routes: list[ModelRoute], prompt: str, feedback: dict | None = None,
         task_override: str = '') -> list[ModelRoute]:
    """Stable ranking; never selects an unconfigured route or stores the prompt."""
    valid_tasks = {'general', 'code', 'research', 'reasoning'}
    task = (
        task_override
        if isinstance(task_override, str) and task_override in valid_tasks
        else task_for(prompt)
    )
    feedback = feedback if isinstance(feedback, dict) else {}

    def score(route):
        identity = (str(route.name) + ' ' + str(route.model)).lower()
        match = (task == 'code' and any(x in identity for x in ('coder', 'codex', 'code', 'qwen'))
                 or task == 'reasoning' and any(x in identity for x in ('reason', 'nemotron', 'deepseek'))
                 or task == 'research' and any(x in identity for x in ('search', 'research')))
        stats = feedback.get(route.name, {})
        if not isinstance(stats, dict):
            stats = {}
        success = stats.get('success', 0)
        failure = stats.get('failure', 0)
        success = success if isinstance(success, (int, float)) else 0
        failure = failure if isinstance(failure, (int, float)) else 0
        denominator = success + failure + 2
        session_reliability = (success + 1) / denominator if denominator > 0 else 0.5
        runtime = route_health(route.name)
        runtime_reliability = float(runtime.get('reliability', 0.5))
        latency_ms = float(runtime.get('latency_ema_ms', 0.0) or 0.0)
        latency_penalty = min(1.25, latency_ms / 12000.0)
        cooldown_penalty = 100.0 if not runtime.get('available', True) else 0.0
        reliability = (session_reliability * 0.45) + (runtime_reliability * 0.55)
        return 2 * bool(match) + 4 * reliability - latency_penalty - cooldown_penalty
    return sorted(routes, key=score, reverse=True)


def record(feedback: dict, route: str, succeeded: bool) -> None:
    """Store only per-route success counts, never prompts or responses."""
    if not route:
        return
    stats = feedback.setdefault(route, {'success':0, 'failure':0})
    key = 'success' if succeeded else 'failure'
    stats[key] = min(stats[key] + 1, 1000)


def free_hf_routes(catalog: dict, key: str, limit: int = 5) -> list[ModelRoute]:
    """Only currently advertised free and live text chat routes; no price assumptions."""
    entries = catalog.get('data', []) if isinstance(catalog, dict) else []
    routes = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str):
            continue
        architecture = entry.get('architecture') or {}
        if 'text' not in architecture.get('output_modalities', []):
            continue
        providers = entry.get('providers') or []
        if not any(isinstance(p, dict) and p.get('status') == 'live' and p.get('is_free') is True
                   for p in providers):
            continue
        model = entry['id']
        if len(model) > 100 or any(c.isspace() for c in model):
            continue
        routes.append(ModelRoute(model, HF_BASE, model, key))
        if len(routes) == limit:
            break
    return routes


async def discover_hf(key: str) -> list[ModelRoute]:
    if not key:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(HF_BASE + '/models', headers={'Authorization':f'Bearer {key}'})
        response.raise_for_status()
    return free_hf_routes(response.json(), key)
