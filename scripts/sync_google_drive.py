"""Mirror Itachi recovery snapshots to a dedicated Google Drive account.

Requires a one-time OAuth authorization by the account owner. The refresh token
is then kept only in GitHub Actions secrets. Public Streamlit users never see it.
"""
from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "data" / "public_catalog.json",
    ROOT / "data" / "knowledge" / "public_knowledge.jsonl",
    ROOT / "data" / "knowledge" / "state.json",
]
TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
DEFAULT_FOLDER_ID = "1fFi6bHUEgjU5cz9M9V8uYaNme1cGgX37"


def access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Google OAuth token response did not contain an access token")
    return token


def _quote_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def find_file(client: httpx.Client, name: str, folder_id: str, api_key: str = "") -> str | None:
    clauses = [f"name = '{_quote_query(name)}'", "trashed = false"]
    if folder_id:
        clauses.append(f"'{_quote_query(folder_id)}' in parents")
    response = client.get(
        DRIVE_API + "/files",
        params={
            "q": " and ".join(clauses),
            "spaces": "drive",
            "fields": "files(id,name)",
            "pageSize": 10,
        },
        headers={"x-goog-api-key": api_key} if api_key else None,
    )
    response.raise_for_status()
    files = response.json().get("files", [])
    if not isinstance(files, list) or not files:
        return None
    item = files[0]
    return item.get("id") if isinstance(item, dict) else None


def create_metadata(client: httpx.Client, name: str, folder_id: str, api_key: str = "") -> str:
    payload: dict[str, object] = {"name": name}
    if folder_id:
        payload["parents"] = [folder_id]
    response = client.post(
        DRIVE_API + "/files",
        params={"fields": "id"},
        headers={"x-goog-api-key": api_key} if api_key else None,
        json=payload,
    )
    response.raise_for_status()
    file_id = response.json().get("id")
    if not isinstance(file_id, str) or not file_id:
        raise RuntimeError("Google Drive did not return a file ID")
    return file_id


def upload_file(client: httpx.Client, path: Path, folder_id: str, api_key: str = "") -> str:
    file_id = find_file(client, path.name, folder_id, api_key)
    if file_id is None:
        file_id = create_metadata(client, path.name, folder_id, api_key)
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    response = client.patch(
        UPLOAD_API + f"/files/{file_id}",
        params={"uploadType": "media"},
        headers={
            "Content-Type": mime,
            **({"x-goog-api-key": api_key} if api_key else {}),
        },
        content=path.read_bytes(),
    )
    response.raise_for_status()
    return file_id


if __name__ == "__main__":
    client_id = os.getenv("ITACHI_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("ITACHI_GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("ITACHI_GOOGLE_REFRESH_TOKEN", "").strip()
    folder_id = os.getenv("ITACHI_GOOGLE_DRIVE_FOLDER_ID", DEFAULT_FOLDER_ID).strip() or DEFAULT_FOLDER_ID
    api_key = os.getenv("ITACHI_GOOGLE_API_KEY", "").strip()

    if not all((client_id, client_secret, refresh_token)):
        print("Google Drive recovery mirror not configured")
        raise SystemExit(0)

    token = access_token(client_id, client_secret, refresh_token)
    headers = {"Authorization": "Bearer " + token}
    completed = []
    with httpx.Client(timeout=30, headers=headers) as client:
        for path in FILES:
            if not path.exists():
                continue
            completed.append((path.name, upload_file(client, path, folder_id, api_key)))

    print("Google Drive recovery files updated:", json.dumps(completed))
