"""Bounded retrieval over Itachi's checked-in public knowledge snapshot."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

FILE = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "public_knowledge.jsonl"
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{2,}")


def _safe_https(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.hostname) and "." in parts.hostname


def load(max_records: int = 1500) -> list[dict]:
    """Load only bounded, public, provenance-carrying records."""
    try:
        if FILE.stat().st_size > 5_000_000:
            raise ValueError("Public knowledge exceeds size limit")
        rows = []
        with FILE.open(encoding="utf-8") as handle:
            for line in handle:
                if len(rows) >= max_records:
                    break
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "")
                title = str(item.get("title") or "")[:240]
                text = str(item.get("text") or "")[:1800]
                if not _safe_https(url) or not title or not text:
                    continue
                rows.append({
                    "title": title,
                    "url": url,
                    "text": text,
                    "source_type": str(item.get("source_type") or "web")[:40],
                    "fetched_at": str(item.get("fetched_at") or "")[:50],
                    "license": str(item.get("license") or "UNKNOWN")[:100],
                })
        return rows
    except (OSError, ValueError):
        return []


def _tokens(text: str) -> set[str]:
    return {match.group(0).casefold() for match in TOKEN.finditer(text)}


def search(query: str, records: list[dict] | None = None, limit: int = 5) -> list[dict]:
    records = records if records is not None else load()
    q = _tokens(query)
    if not q:
        return []
    ranked = []
    for item in records:
        title_tokens = _tokens(item["title"])
        body_tokens = _tokens(item["text"])
        title_hits = len(q & title_tokens)
        body_hits = len(q & body_tokens)
        if not title_hits and not body_hits:
            continue
        denominator = math.sqrt(max(1, len(body_tokens)))
        score = (title_hits * 3.0) + (body_hits / denominator)
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[: max(1, min(limit, 8))]]


def context(items: list[dict]) -> str:
    if not items:
        return "(none)"
    chunks = []
    for item in items:
        clean = " ".join(item["text"].split())
        chunks.append(
            f"- {item['title']}\n"
            f"  Source: {item['url']}\n"
            f"  Type: {item['source_type']}\n"
            f"  Excerpt: {clean[:900]}"
        )
    return "\n".join(chunks)
