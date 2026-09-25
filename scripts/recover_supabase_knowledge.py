"""Recover the checked-in Itachi public knowledge snapshot from Supabase."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "knowledge" / "public_knowledge.jsonl"


def _headers(key: str) -> dict[str, str]:
    headers = {"apikey": key, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    return headers


if __name__ == "__main__":
    url = os.getenv("ITACHI_SUPABASE_URL", "").strip()
    key = (
        os.getenv("ITACHI_SUPABASE_SERVER_KEY", "").strip()
        or os.getenv("ITACHI_SUPABASE_ANON_KEY", "").strip()
    )
    if not url or not key:
        raise SystemExit("Supabase recovery requires ITACHI_SUPABASE_URL and a read-capable key")

    endpoint = url.rstrip("/") + "/rest/v1/itachi_public_knowledge"
    params = {
        "select": "url,title,content,source_type,license,content_sha256,fetched_at",
        "order": "fetched_at.desc",
        "limit": "1500",
    }
    with httpx.Client(timeout=30, headers=_headers(key)) as client:
        response = client.get(endpoint, params=params)
        response.raise_for_status()
        rows = response.json()

    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Supabase recovery returned no public knowledge")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with DEST.open("w", encoding="utf-8") as handle:
        for row in rows:
            item = {
                "title": row["title"],
                "url": row["url"],
                "text": row["content"],
                "source_type": row.get("source_type", "web"),
                "license": row.get("license", "UNKNOWN"),
                "content_sha256": row["content_sha256"],
                "fetched_at": row["fetched_at"],
            }
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    print("Recovered", len(rows), "public knowledge records from Supabase")
