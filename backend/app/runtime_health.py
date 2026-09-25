"""Small in-process health registry for external capabilities and model routes."""
from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class HealthState:
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    last_error: str = ""
    latency_ema_ms: float = 0.0


_STATES: dict[str, HealthState] = {}


def _state(name: str) -> HealthState:
    return _STATES.setdefault(name, HealthState())


def reset() -> None:
    """Testing/admin helper."""
    _STATES.clear()


def available(name: str, now: float | None = None) -> bool:
    state = _state(name)
    current = time.monotonic() if now is None else float(now)
    return current >= state.cooldown_until


def _cooldown_for(error: Exception, consecutive_failures: int) -> float:
    text = str(error).lower()
    status = getattr(getattr(error, "response", None), "status_code", None)
    if status in {401, 403} or "unauthorized" in text or "forbidden" in text:
        return 900.0
    if status == 429 or "rate limit" in text or "quota" in text:
        return 120.0
    if status == 404 or "model not found" in text or "unknown model" in text:
        return 600.0
    base = 15.0 * (2 ** max(0, min(consecutive_failures - 1, 4)))
    return min(base, 240.0)


def record_success(name: str, latency_ms: float | None = None) -> None:
    state = _state(name)
    state.successes += 1
    state.consecutive_failures = 0
    state.cooldown_until = 0.0
    state.last_success = time.time()
    state.last_error = ""
    if latency_ms is not None and latency_ms >= 0:
        value = float(latency_ms)
        state.latency_ema_ms = (
            value if state.latency_ema_ms <= 0
            else (state.latency_ema_ms * 0.75) + (value * 0.25)
        )


def record_failure(name: str, error: Exception) -> None:
    state = _state(name)
    state.failures += 1
    state.consecutive_failures += 1
    state.last_failure = time.time()
    state.last_error = type(error).__name__
    state.cooldown_until = time.monotonic() + _cooldown_for(
        error,
        state.consecutive_failures,
    )


def snapshot(name: str) -> dict[str, float | int | str | bool]:
    state = _state(name)
    total = state.successes + state.failures
    reliability = (state.successes + 1) / (total + 2)
    remaining = max(0.0, state.cooldown_until - time.monotonic())
    return {
        "available": remaining <= 0.0,
        "successes": state.successes,
        "failures": state.failures,
        "consecutive_failures": state.consecutive_failures,
        "cooldown_remaining": remaining,
        "last_success": state.last_success,
        "last_failure": state.last_failure,
        "last_error": state.last_error,
        "latency_ema_ms": state.latency_ema_ms,
        "reliability": reliability,
    }
