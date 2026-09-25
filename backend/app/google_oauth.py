"""One-time Google OAuth bootstrap for Itachi's dedicated Drive account."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_CLIENT_ID = "317302743552-dhhbejneka99apadpp6ocvq8sa5rn21p.apps.googleusercontent.com"
DEFAULT_REDIRECT_URI = "https://project-itachi.streamlit.app"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
STATE_TTL_SECONDS = 15 * 60


def oauth_config(raw_json: str = "", client_id: str = "", client_secret: str = "",
                 redirect_uri: str = "") -> tuple[str, str, str]:
    """Resolve OAuth settings without ever requiring the client secret in source."""
    if raw_json.strip():
        try:
            payload = json.loads(raw_json)
            web = payload.get("web", {})
        except (json.JSONDecodeError, AttributeError, TypeError) as error:
            raise ValueError("Invalid Google OAuth JSON") from error
        if not isinstance(web, dict):
            raise ValueError("Google OAuth JSON must contain a web object")
        client_id = str(web.get("client_id") or client_id)
        client_secret = str(web.get("client_secret") or client_secret)
        uris = web.get("redirect_uris") or []
        if not redirect_uri and isinstance(uris, list) and uris:
            redirect_uri = str(uris[0])

    client_id = client_id.strip() or DEFAULT_CLIENT_ID
    client_secret = client_secret.strip()
    redirect_uri = redirect_uri.strip() or DEFAULT_REDIRECT_URI
    if not client_secret:
        raise ValueError("Google OAuth client secret is not configured")
    return client_id, client_secret, redirect_uri


def issue_state(signing_secret: str, now: int | None = None) -> str:
    timestamp = int(now if now is not None else time.time())
    nonce = secrets.token_urlsafe(18)
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(
        signing_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload}.{encoded}"


def valid_state(state: str, signing_secret: str, now: int | None = None) -> bool:
    try:
        timestamp_text, nonce, supplied = state.split(".", 2)
        timestamp = int(timestamp_text)
    except (AttributeError, ValueError):
        return False
    current = int(now if now is not None else time.time())
    if timestamp > current + 60 or current - timestamp > STATE_TTL_SECONDS:
        return False
    payload = f"{timestamp}.{nonce}"
    expected = base64.urlsafe_b64encode(
        hmac.new(
            signing_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("ascii").rstrip("=")
    return hmac.compare_digest(expected, supplied)


def authorization_url(client_id: str, redirect_uri: str, state: str,
                      login_hint: str = "") -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DRIVE_FILE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    if login_hint:
        params["login_hint"] = login_hint
    return GOOGLE_AUTH_URL + "?" + urlencode(params)


async def exchange_code(code: str, client_id: str, client_secret: str,
                        redirect_uri: str, timeout: float = 20.0) -> dict:
    if not code.strip():
        raise ValueError("Google OAuth authorization code is missing")
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Google token response is invalid")
    return payload
