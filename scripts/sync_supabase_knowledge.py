"""Replicate Itachi's public knowledge snapshot to Supabase.

This script is intended for GitHub Actions. It requires a dedicated Supabase
server-side key in repository secrets. It never receives end-user chat data.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "data" / "knowledge" / "public_knowledge.jsonl"
STATE = ROOT / "data" / "knowledge" / "state.json"


def _headers(key: str) -> dict[str, str]:
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    # Legacy service-role JWTs are valid bearer tokens. New sb_secret_* keys
    # belong in the apikey header and must not be sent as bearer tokens.
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    return headers


def _load_rows() -> list[dict]:
    rows = []
    for line in KNOWLEDGE.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        rows.append({
            "url": item["url"],
            "title": item["title"],
            "content": item["text"],
            "source_type": item.get("source_type", "web"),
            "license": item.get("license", "UNKNOWN"),
            "content_sha256": item["content_sha256"],
            "fetched_at": item["fetched_at"],
            "metadata": {"mirror": "github-actions"},
        })
    return rows


def sync_database(base_url: str, key: str, rows: list[dict]) -> None:
    endpoint = base_url.rstrip("/") + "/rest/v1/itachi_public_knowledge"
    headers = _headers(key)
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    with httpx.Client(timeout=30, headers=headers) as client:
        for start in range(0, len(rows), 100):
            response = client.post(
                endpoint,
                params={"on_conflict": "url"},
                json=rows[start:start + 100],
            )
            response.raise_for_status()


def sync_recovery_object(base_url: str, key: str) -> None:
    """Best-effort snapshot to Supabase Storage; DB remains the main replica."""
    endpoint = (
        base_url.rstrip("/")
        + "/storage/v1/object/itachi-recovery/public_knowledge.jsonl"
    )
    headers = {
        "apikey": key,
        "Content-Type": "application/x-ndjson",
        "x-upsert": "true",
    }
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    with httpx.Client(timeout=30, headers=headers) as client:
        response = client.post(endpoint, content=KNOWLEDGE.read_bytes())
        if response.status_code >= 400:
            print("Supabase Storage backup skipped:", response.status_code, response.text[:200])


if __name__ == "__main__":
    url = os.getenv("ITACHI_SUPABASE_URL", "").strip()
    key = os.getenv("ITACHI_SUPABASE_SERVER_KEY", "").strip()
    if not url or not key:
        print("Supabase replica not configured; GitHub remains the primary durable store")
        raise SystemExit(0)

    rows = _load_rows()
    if not rows:
        raise RuntimeError("Refusing to replace cloud replica with an empty knowledge set")

    sync_database(url, key, rows)
    sync_recovery_object(url, key)

    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    print("Supabase knowledge replica updated:", len(rows), "records", state.get("generated_at"))
