"""Vercel FastAPI entrypoint for Project Itachi."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.app.answer_guard import guaranteed_answer
from backend.app.autonomy import requires_fresh_web
from backend.app.client_context import client_context_text, local_clock_reply, weather_reply
from backend.app.jev import evaluate_prompt as jev_evaluate_prompt
from backend.app.model_catalog import ModelRoute, parse
from backend.app.model_selection import rank
from backend.app.public_knowledge import (
    context as learned_context,
    load as load_learned_knowledge,
    search as search_learned_knowledge,
)

app = FastAPI(title="ITACHI", docs_url=None, redoc_url=None)

LEARNED_KNOWLEDGE = load_learned_knowledge()
SESSION_COOKIE = "itachi_preview_session"
SESSION_MAX_AGE = 8 * 60 * 60
VERCEL_BRIDGED_PATHS = {
    "/api/status",
    "/api/health",
    "/api/unlock",
    "/api/chat",
}


@app.middleware("http")
async def _restore_vercel_api_path(request: Request, call_next):
    """Restore API subpaths forwarded through the single /api Python function.

    In this mixed Next.js/Python deployment, Vercel exposes ``api/index.py`` at
    the exact ``/api`` path. The Next.js catch-all route forwards API requests
    to that function and passes the original, allowlisted path in a header.
    """
    original_path = request.headers.get("x-itachi-original-path", "")
    if request.url.path == "/api" and original_path in VERCEL_BRIDGED_PATHS:
        request.scope["path"] = original_path
        request.scope["raw_path"] = original_path.encode("ascii")
    return await call_next(request)


@app.exception_handler(Exception)
async def _unhandled_error(_: Request, __: Exception):
    """Never expose internal exception details or provider failures to browsers."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Itachi could not complete the request. Please try again shortly."},
    )


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class BrowserContext(BaseModel):
    timezone: str = Field(default="UTC", max_length=80)
    locale: str = Field(default="", max_length=40)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)


class UnlockRequest(BaseModel):
    passcode: str = Field(default="", max_length=256)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    depth: Literal["auto", "quick", "standard", "deep"] = "auto"
    history: list[Turn] = Field(default_factory=list, max_length=12)
    browser: BrowserContext = Field(default_factory=BrowserContext)


def _setting(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "")


def _access_required() -> bool:
    return bool(_setting("ITACHI_ACCESS_PASSCODE"))


def _authorized(passcode: str) -> bool:
    expected = _setting("ITACHI_ACCESS_PASSCODE")
    if not expected:
        return True
    return hmac.compare_digest(str(passcode or ""), expected)


def _session_token(expires_at: int) -> str:
    secret = _setting("ITACHI_ACCESS_PASSCODE")
    if not secret:
        return ""
    message = f"itachi-session:{expires_at}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"


def _session_authorized(request: Request) -> bool:
    if not _access_required():
        return True
    token = str(request.cookies.get(SESSION_COOKIE) or "")
    try:
        expires_text, signature = token.split(".", 1)
        expires_at = int(expires_text)
    except (TypeError, ValueError):
        return False
    now = int(time.time())
    if expires_at <= now or expires_at > now + SESSION_MAX_AGE + 60:
        return False
    expected = _session_token(expires_at)
    return bool(expected and hmac.compare_digest(token, expected))


def _configured_routes() -> list[ModelRoute]:
    routes: list[ModelRoute] = []
    raw = _setting("ITACHI_MODEL_ROUTES_JSON")
    if raw:
        try:
            routes = [
                route for route in parse(raw)
                if route.url.startswith("https://")
            ]
        except ValueError:
            routes = []

    if not routes:
        for name, prefix in (("Reasoning", "REASONING"), ("Fallback", "FALLBACK")):
            url = _setting(f"ITACHI_{prefix}_URL")
            model = _setting(f"ITACHI_{prefix}_MODEL")
            if url and model and not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
                routes.append(ModelRoute(name, url, model, _setting(f"ITACHI_{prefix}_KEY")))

    candidates = [
        (
            "NVIDIA Nemotron Ultra",
            _setting("ITACHI_NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/"),
            _setting("ITACHI_NVIDIA_CHAT_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"),
            _setting("ITACHI_NVIDIA_API_KEY"),
        ),
        ("Groq Qwen", "https://api.groq.com/openai/v1", "qwen/qwen3.8-27b", _setting("ITACHI_GROQ_API_KEY")),
        (
            "Gemini Flash",
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "gemini-3.8-flash",
            _setting("ITACHI_GEMINI_API_KEY"),
        ),
        ("Cerebras GPT OSS", "https://api.cerebras.ai/v1", "gpt-oss-120b", _setting("ITACHI_CEREBRAS_API_KEY")),
        ("OpenRouter Free", "https://openrouter.ai/api/v1", "openrouter/free", _setting("ITACHI_OPENROUTER_API_KEY")),
    ]
    known = {route.name for route in routes}
    for name, url, model, key in candidates:
        if key and name not in known and len(routes) < 5:
            routes.append(ModelRoute(name, url, model, key))
            known.add(name)
    return routes[:5]


def _history_context(history: list[Turn]) -> str:
    if not history:
        return "(none)"
    lines = []
    for turn in history[-8:]:
        label = "User" if turn.role == "user" else "Itachi"
        lines.append(f"{label}: {turn.content[:1800]}")
    return "\n".join(lines)


def _strip_weather_source(text: str) -> str:
    marker = "\n\nWeather data:"
    index = text.find(marker)
    return text[:index].rstrip() if index >= 0 else text.strip()


@app.get("/api/status")
async def status():
    return {
        "ready": True,
        "accessRequired": _access_required(),
        "routesConfigured": bool(_configured_routes()),
    }


@app.post("/api/unlock")
async def unlock(payload: UnlockRequest, response: Response):
    if not _authorized(payload.passcode):
        raise HTTPException(status_code=401, detail="Invalid access passcode")
    if _access_required():
        expires_at = int(time.time()) + SESSION_MAX_AGE
        response.set_cookie(
            key=SESSION_COOKIE,
            value=_session_token(expires_at),
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=_setting("VERCEL") == "1",
            samesite="strict",
            path="/",
        )
    return {"ok": True}


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request):
    if not _session_authorized(request):
        raise HTTPException(status_code=401, detail="Access required")

    prompt = payload.prompt.strip()
    browser = payload.browser

    local = local_clock_reply(
        prompt,
        browser.timezone,
        browser.locale,
        browser.latitude,
        browser.longitude,
        browser.accuracy,
    )
    if local:
        return {"answer": local}

    try:
        weather = await weather_reply(
            prompt,
            browser.timezone,
            browser.locale,
            browser.latitude,
            browser.longitude,
        )
    except Exception:
        weather = None
    if weather:
        return {"answer": _strip_weather_source(weather)}

    routes = _configured_routes()

    fresh = requires_fresh_web(prompt)
    task_override = ""
    typesafe_key = _setting("TYPESAFE_API_KEY", _setting("ITACHI_JEV_TOKEN"))
    if typesafe_key:
        try:
            decision = await jev_evaluate_prompt(prompt, typesafe_key)
            task_override = decision.task
        except Exception:
            task_override = ""

    learned = search_learned_knowledge(
        prompt,
        LEARNED_KNOWLEDGE,
        limit=5,
        fresh=fresh,
    )
    browser_context = client_context_text(
        browser.timezone,
        browser.locale,
        browser.latitude is not None and browser.longitude is not None,
    )
    extra_context = (
        "Recent conversation:\n"
        + _history_context(payload.history)
        + "\n\nBrowser context:\n"
        + browser_context
        + "\n\nLearned public knowledge:\n"
        + learned_context(learned)
    )

    ordered = rank(routes, prompt, task_override=task_override)
    answer, _ = await guaranteed_answer(
        prompt,
        ordered,
        _setting("ITACHI_TAVILY_KEY"),
        allow_web=True,
        depth=payload.depth,
        extra_context=extra_context,
        rapidapi_key=_setting("ITACHI_RAPIDAPI_KEY"),
    )
    return {"answer": answer}


@app.get("/api/health")
async def health():
    return {"status": "ready"}
