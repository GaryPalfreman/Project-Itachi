"""Hosted semantic memory backed by NVIDIA Nemotron embeddings.

The embedder is stateless and remote. The default in-memory store is intentionally
session-scoped so Streamlit Community Cloud does not persist chat data to disk.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Iterable

import httpx

from .runtime_health import available, record_failure, record_success

NVIDIA_EMBEDDINGS_URL = "https://integrate.api.nvidia.com/v1/embeddings"
NEMOTRON_MODEL = "nvidia/nemotron-3-embed-1b"
NEMOTRON_DIMENSIONS = 2048


async def embed(
    text: str,
    api_key: str,
    *,
    input_type: str,
    url: str = NVIDIA_EMBEDDINGS_URL,
    timeout: float = 30.0,
) -> list[float]:
    """Return one Nemotron embedding for a query or passage."""
    if input_type not in {"query", "passage"}:
        raise ValueError("input_type must be 'query' or 'passage'")
    if not api_key:
        raise ValueError("NVIDIA API key is required for hosted embeddings")
    if not text.strip():
        raise ValueError("text must not be empty")

    payload = {
        "model": NEMOTRON_MODEL,
        "input": text,
        "input_type": input_type,
        "encoding_format": "float",
        "truncate": "END",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    health_key = "external:embeddings"
    if not available(health_key):
        raise RuntimeError("Embedding service is temporarily cooling down")
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        record_success(health_key, (time.perf_counter() - started) * 1000.0)
    except Exception as error:
        record_failure(health_key, error)
        raise

    vector = body["data"][0]["embedding"]
    if len(vector) != NEMOTRON_DIMENSIONS:
        raise ValueError(
            f"Expected {NEMOTRON_DIMENSIONS} dimensions, got {len(vector)}"
        )
    return [float(value) for value in vector]


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    a = list(left)
    b = list(right)
    if len(a) != len(b):
        raise ValueError("vectors must have the same dimensions")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class MemoryItem:
    text: str
    vector: list[float]
    role: str = "user"
    created_at: float = field(default_factory=time.time)
    volatile: bool = False


@dataclass
class SessionSemanticMemory:
    """Small session-local vector store suitable for Streamlit session_state."""

    items: list[MemoryItem] = field(default_factory=list)
    max_items: int = 80

    def add(
        self,
        text: str,
        vector: list[float],
        role: str = "user",
        *,
        volatile: bool = False,
    ) -> None:
        self.items.append(
            MemoryItem(text=text, vector=vector, role=role, volatile=volatile)
        )
        if len(self.items) > self.max_items:
            del self.items[: len(self.items) - self.max_items]

    def recall(
        self,
        query_vector: list[float],
        *,
        limit: int = 4,
        min_similarity: float = 0.28,
        fresh_query: bool = False,
        volatile_max_age: float = 900.0,
    ) -> list[tuple[MemoryItem, float]]:
        now = time.time()
        eligible = [
            item for item in self.items
            if not item.volatile
            or (
                not fresh_query
                and max(0.0, now - item.created_at) <= volatile_max_age
            )
        ]
        scored = [
            (item, cosine_similarity(query_vector, item.vector))
            for item in eligible
        ]
        scored = [entry for entry in scored if entry[1] >= min_similarity]
        scored.sort(key=lambda entry: entry[1], reverse=True)
        return scored[:limit]


def format_context(matches: list[tuple[MemoryItem, float]]) -> str:
    if not matches:
        return "(none)"
    lines = []
    for item, score in matches:
        clean = " ".join(item.text.split())
        lines.append(f"- [{item.role}; similarity={score:.3f}] {clean[:900]}")
    return "\n".join(lines)
