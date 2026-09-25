"""Continuously refresh bounded public knowledge using no personal credentials.

Runs in GitHub Actions with GitHub's ephemeral workflow token. It never executes
downloaded repository code. It stores public metadata, short excerpts, source
URLs, licenses and timestamps for provenance-aware retrieval.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx

from backend.app.public_sources import wikipedia

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "sources" / "learning_sources.json"
DEST = ROOT / "data" / "knowledge" / "public_knowledge.jsonl"
STATE = ROOT / "data" / "knowledge" / "state.json"
AGENT = "ProjectItachi/0.4 (+https://github.com/GaryPalfreman/Project-Itachi)"
LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0"}
SPACE = re.compile(r"\s+")


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_html(value: str, limit: int = 1400) -> str:
    parser = PlainText()
    try:
        parser.feed(value or "")
    except Exception:
        return ""
    return SPACE.sub(" ", unescape(" ".join(parser.parts))).strip()[:limit]


def record(*, title: str, url: str, text: str, source_type: str,
           license_name: str = "UNKNOWN") -> dict | None:
    title = SPACE.sub(" ", title).strip()[:240]
    text = SPACE.sub(" ", text).strip()[:1800]
    if not title or not url.startswith("https://") or not text:
        return None
    return {
        "title": title,
        "url": url[:700],
        "text": text,
        "source_type": source_type[:40],
        "license": license_name[:100],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def load_existing() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not DEST.exists():
        return rows
    try:
        for line in DEST.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                rows[item["url"]] = item
    except (OSError, json.JSONDecodeError):
        return {}
    return rows


async def github_readme(client: httpx.AsyncClient, full_name: str) -> str:
    try:
        response = await client.get(f"https://api.github.com/repos/{full_name}/readme")
        response.raise_for_status()
        payload = response.json()
        encoded = payload.get("content", "") if isinstance(payload, dict) else ""
        if not isinstance(encoded, str):
            return ""
        raw = base64.b64decode(encoded.encode("ascii"), validate=False).decode("utf-8", "replace")
        return SPACE.sub(" ", raw).strip()[:1800]
    except (httpx.HTTPError, ValueError, UnicodeError):
        return ""


async def github_repo(client: httpx.AsyncClient, full_name: str) -> dict | None:
    try:
        response = await client.get(f"https://api.github.com/repos/{full_name}")
        response.raise_for_status()
        item = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    license_data = item.get("license") or {}
    spdx = str(license_data.get("spdx_id") or "UNKNOWN")
    if spdx not in LICENSES:
        return None
    readme = await github_readme(client, full_name)
    description = str(item.get("description") or "")
    text = readme or description
    return record(
        title=full_name,
        url=f"https://github.com/{full_name}",
        text=text,
        source_type="github_readme",
        license_name=spdx,
    )


async def discover_repositories(client: httpx.AsyncClient, topic: str, limit: int = 2) -> list[dict]:
    try:
        response = await client.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{topic[:90]} archived:false fork:false",
                "sort": "stars",
                "order": "desc",
                "per_page": max(1, min(limit * 3, 6)),
            },
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except (httpx.HTTPError, ValueError):
        return []
    found = []
    for item in items:
        full_name = item.get("full_name") if isinstance(item, dict) else None
        if not isinstance(full_name, str):
            continue
        learned = await github_repo(client, full_name)
        if learned:
            found.append(learned)
        if len(found) >= limit:
            break
    return found


async def fetch_feed(client: httpx.AsyncClient, name: str, url: str) -> list[dict]:
    try:
        response = await client.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except (httpx.HTTPError, ET.ParseError, ValueError):
        return []

    rows = []
    entries = list(root.findall(".//item")) + list(root.findall(".//{*}entry"))
    for entry in entries[:12]:
        title = (entry.findtext("title") or entry.findtext("{*}title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        if not link:
            link_node = entry.find("{*}link")
            if link_node is not None:
                link = str(link_node.attrib.get("href") or "").strip()
        summary = (
            entry.findtext("description")
            or entry.findtext("{*}summary")
            or entry.findtext("{*}content")
            or ""
        )
        learned = record(
            title=f"{name}: {title}",
            url=link,
            text=clean_html(summary),
            source_type="feed",
            license_name="SOURCE TERMS",
        )
        if learned:
            rows.append(learned)
    return rows


async def build() -> tuple[list[dict], dict]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token

    existing = load_existing()
    fresh: list[dict] = []
    stats = {"wikipedia": 0, "github": 0, "feeds": 0}

    for topic in config.get("topics", [])[:6]:
        if not isinstance(topic, str):
            continue
        try:
            pages = await wikipedia(topic)
        except Exception:
            pages = []
        for page in pages[:3]:
            learned = record(
                title=str(page.get("title") or topic),
                url=str(page.get("url") or ""),
                text=str(page.get("excerpt") or ""),
                source_type="wikipedia",
                license_name="CC BY-SA",
            )
            if learned:
                fresh.append(learned)
                stats["wikipedia"] += 1

    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
        for full_name in config.get("repositories", [])[:8]:
            if isinstance(full_name, str):
                learned = await github_repo(client, full_name)
                if learned:
                    fresh.append(learned)
                    stats["github"] += 1

        for topic in config.get("topics", [])[:5]:
            if isinstance(topic, str):
                discovered = await discover_repositories(client, topic, limit=2)
                fresh.extend(discovered)
                stats["github"] += len(discovered)

        for feed in config.get("feeds", [])[:5]:
            if not isinstance(feed, dict):
                continue
            name, url = feed.get("name"), feed.get("url")
            if isinstance(name, str) and isinstance(url, str) and url.startswith("https://"):
                learned = await fetch_feed(client, name, url)
                fresh.extend(learned)
                stats["feeds"] += len(learned)

    merged = existing
    for item in fresh:
        merged[item["url"]] = item

    rows = sorted(
        merged.values(),
        key=lambda item: str(item.get("fetched_at") or ""),
        reverse=True,
    )[:1500]
    state = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(rows),
        "fresh_counts": stats,
        "policy": "Public sources only; short excerpts; downloaded code is never executed.",
    }
    return rows, state


if __name__ == "__main__":
    rows, state = asyncio.run(build())
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print("Itachi public knowledge records:", len(rows), state["fresh_counts"])
