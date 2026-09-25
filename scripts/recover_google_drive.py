"""Recover Itachi's public knowledge snapshot from a dedicated Google Drive account."""
from __future__ import annotations

import os
from pathlib import Path

import httpx

from scripts.sync_google_drive import DRIVE_API, DEFAULT_FOLDER_ID, access_token, find_file

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "public_catalog.json": ROOT / "data" / "public_catalog.json",
    "public_knowledge.jsonl": ROOT / "data" / "knowledge" / "public_knowledge.jsonl",
    "state.json": ROOT / "data" / "knowledge" / "state.json",
}


def download_file(client: httpx.Client, file_id: str, destination: Path, api_key: str = "") -> None:
    response = client.get(
        DRIVE_API + f"/files/{file_id}",
        params={"alt": "media", **({"key": api_key} if api_key else {})},
    )
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


if __name__ == "__main__":
    client_id = os.getenv("ITACHI_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("ITACHI_GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("ITACHI_GOOGLE_REFRESH_TOKEN", "").strip()
    folder_id = os.getenv("ITACHI_GOOGLE_DRIVE_FOLDER_ID", DEFAULT_FOLDER_ID).strip() or DEFAULT_FOLDER_ID
    api_key = os.getenv("ITACHI_GOOGLE_API_KEY", "").strip()

    if not all((client_id, client_secret, refresh_token)):
        raise SystemExit("Google Drive recovery credentials are not configured")

    token = access_token(client_id, client_secret, refresh_token)
    headers = {"Authorization": "Bearer " + token}
    recovered = []
    with httpx.Client(timeout=30, headers=headers) as client:
        for name, destination in TARGETS.items():
            file_id = find_file(client, name, folder_id, api_key)
            if not file_id:
                continue
            download_file(client, file_id, destination, api_key)
            recovered.append(name)

    if "public_knowledge.jsonl" not in recovered:
        raise RuntimeError("Google Drive recovery did not contain public_knowledge.jsonl")
    print("Recovered from Google Drive:", ", ".join(recovered))
