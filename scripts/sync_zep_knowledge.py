"""Throttled optional replication of learned public facts to Zep Cloud.

Uses the official Zep SDK only when a dedicated Itachi Zep API key is configured.
The state file prevents duplicate ingestion and limits free-tier credit use.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "data" / "knowledge" / "public_knowledge.jsonl"
STATE = ROOT / "data" / "knowledge" / "zep_state.json"
MIN_INTERVAL_SECONDS = 6 * 60 * 60
MAX_RECORDS_PER_RUN = 3
DEFAULT_GROUP_ID = "project-itachi-public-knowledge"


def load_state() -> dict:
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_candidates(sent: set[str]) -> list[dict]:
    rows = []
    if not KNOWLEDGE.exists():
        return rows
    for line in KNOWLEDGE.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        digest = str(item.get("content_sha256") or "")
        if digest and digest not in sent:
            rows.append(item)
    rows.sort(key=lambda item: str(item.get("fetched_at") or ""), reverse=True)
    return rows[:MAX_RECORDS_PER_RUN]


if __name__ == "__main__":
    key = os.getenv("ITACHI_ZEP_API_KEY", "").strip()
    if not key:
        print("Zep replica not configured")
        raise SystemExit(0)

    state = load_state()
    now = int(time.time())
    last_run = int(state.get("last_run_epoch") or 0)
    if now - last_run < MIN_INTERVAL_SECONDS:
        print("Zep sync throttled to protect free-tier credits")
        raise SystemExit(0)

    from zep_cloud.client import Zep

    sent = set(state.get("sent_hashes") or [])
    candidates = load_candidates(sent)
    if not candidates:
        print("No new Zep knowledge records")
        state["last_run_epoch"] = now
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(0)

    client = Zep(api_key=key)
    group_id = os.getenv("ITACHI_ZEP_GROUP_ID", DEFAULT_GROUP_ID).strip() or DEFAULT_GROUP_ID
    completed = []
    for item in candidates:
        payload = (
            f"Title: {item['title']}\n"
            f"Source: {item['url']}\n"
            f"License: {item.get('license', 'UNKNOWN')}\n"
            f"Fetched: {item.get('fetched_at', '')}\n"
            f"Public reference text: {item['text']}"
        )
        client.graph.add(
            group_id=group_id,
            data=payload,
            type="text",
            source_description="Project Itachi public learning corpus",
        )
        completed.append(item["content_sha256"])

    sent.update(completed)
    state = {
        "last_run_epoch": now,
        "sent_hashes": list(sent)[-2000:],
        "last_batch_count": len(completed),
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print("Zep public knowledge episodes added:", len(completed))
