"""Allowlisted RapidAPI specialist data sources for Itachi.

One shared RapidAPI key is used server-side. The model never controls hosts or paths.
"""
from __future__ import annotations

import asyncio
import json
import time
from urllib.parse import quote

import httpx

ALPHA_HOST = "alpha-vantage.p.rapidapi.com"
GEODB_HOST = "wft-geo-db.p.rapidapi.com"
WORDS_HOST = "wordsapiv1.p.rapidapi.com"
SEARCH_HOST = "real-time-web-search.p.rapidapi.com"

_CACHE: dict[str, tuple[float, object]] = {}


def _headers(key: str, host: str) -> dict[str, str]:
    return {
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": host,
        "Accept": "application/json",
    }


def _cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    expires, value = item
    if time.time() >= expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: object, ttl: int):
    _CACHE[key] = (time.time() + ttl, value)
    if len(_CACHE) > 256:
        for old_key in list(_CACHE)[:64]:
            _CACHE.pop(old_key, None)


async def _get_json(url: str, key: str, host: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(url, headers=_headers(key, host), params=params or {})
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict):
            raise RuntimeError("RapidAPI returned unsupported JSON")
        return value


async def finance_lookup(query: str, key: str) -> str:
    """Resolve a stock/ETF/company query and return a compact live quote."""
    query = str(query or "").strip()[:80]
    if not query or not key:
        return ""
    cache_key = f"finance:{query.casefold()}"
    cached = _cache_get(cache_key)
    if isinstance(cached, str):
        return cached

    search_payload = await _get_json(
        f"https://{ALPHA_HOST}/query",
        key,
        ALPHA_HOST,
        {"function": "SYMBOL_SEARCH", "keywords": query},
    )
    matches = search_payload.get("bestMatches")
    symbol = query.upper()
    match_summary = ""
    if isinstance(matches, list) and matches:
        best = matches[0] if isinstance(matches[0], dict) else {}
        symbol = str(best.get("1. symbol") or symbol)
        match_summary = " | ".join(
            part for part in (
                str(best.get("2. name") or ""),
                str(best.get("4. region") or ""),
                str(best.get("8. currency") or ""),
            ) if part
        )

    quote_payload = await _get_json(
        f"https://{ALPHA_HOST}/query",
        key,
        ALPHA_HOST,
        {"function": "GLOBAL_QUOTE", "symbol": symbol},
    )
    quote_data = quote_payload.get("Global Quote")
    if not isinstance(quote_data, dict) or not quote_data:
        output = f"Market match: {symbol}"
        if match_summary:
            output += f" | {match_summary}"
    else:
        output = (
            f"Live market data for {symbol}"
            + (f" ({match_summary})" if match_summary else "")
            + ": "
            f"price={quote_data.get('05. price', 'n/a')}, "
            f"open={quote_data.get('02. open', 'n/a')}, "
            f"high={quote_data.get('03. high', 'n/a')}, "
            f"low={quote_data.get('04. low', 'n/a')}, "
            f"volume={quote_data.get('06. volume', 'n/a')}, "
            f"latest_trading_day={quote_data.get('07. latest trading day', 'n/a')}, "
            f"change={quote_data.get('09. change', 'n/a')} "
            f"({quote_data.get('10. change percent', 'n/a')})."
        )
    _cache_put(cache_key, output, 120)
    return output


async def city_lookup(query: str, key: str) -> str:
    """Return structured city/region/country candidates."""
    query = str(query or "").strip()[:100]
    if not query or not key:
        return ""
    cache_key = f"city:{query.casefold()}"
    cached = _cache_get(cache_key)
    if isinstance(cached, str):
        return cached

    payload = await _get_json(
        f"https://{GEODB_HOST}/v1/geo/cities",
        key,
        GEODB_HOST,
        {
            "namePrefix": query,
            "limit": 5,
            "offset": 0,
            "sort": "-population",
        },
    )
    rows = payload.get("data")
    lines = []
    if isinstance(rows, list):
        for row in rows[:5]:
            if not isinstance(row, dict):
                continue
            name = str(row.get("city") or row.get("name") or "")
            region = str(row.get("region") or "")
            country = str(row.get("country") or "")
            code = str(row.get("countryCode") or "")
            population = row.get("population")
            lat = row.get("latitude")
            lon = row.get("longitude")
            lines.append(
                ", ".join(part for part in (name, region, country) if part)
                + (f" [{code}]" if code else "")
                + (f"; population={population}" if isinstance(population, (int, float)) else "")
                + (f"; coordinates={lat},{lon}" if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) else "")
            )
    output = "Structured city data: " + (" | ".join(lines) if lines else "no match")
    _cache_put(cache_key, output, 900)
    return output


async def word_lookup(word: str, key: str) -> str:
    """Return lexical data for a single English word."""
    word = str(word or "").strip().lower()[:80]
    if not word or not key or " " in word:
        return ""
    cache_key = f"word:{word}"
    cached = _cache_get(cache_key)
    if isinstance(cached, str):
        return cached

    payload = await _get_json(
        f"https://{WORDS_HOST}/words/{quote(word, safe='')}",
        key,
        WORDS_HOST,
    )
    definitions = []
    synonyms = []
    results = payload.get("results")
    if isinstance(results, list):
        for item in results[:6]:
            if not isinstance(item, dict):
                continue
            definition = str(item.get("definition") or "").strip()
            part = str(item.get("partOfSpeech") or "").strip()
            if definition:
                definitions.append((f"{part}: " if part else "") + definition)
            item_syn = item.get("synonyms")
            if isinstance(item_syn, list):
                synonyms.extend(str(value) for value in item_syn[:8] if value)
    pronunciation = payload.get("pronunciation")
    if isinstance(pronunciation, dict):
        pronunciation = pronunciation.get("all") or pronunciation.get("noun") or pronunciation.get("verb")
    output = (
        f"Lexical data for '{word}': definitions="
        + (" | ".join(definitions[:5]) if definitions else "n/a")
    )
    if synonyms:
        output += "; synonyms=" + ", ".join(dict.fromkeys(synonyms[:12]))
    if pronunciation:
        output += f"; pronunciation={pronunciation}"
    output += "."
    _cache_put(cache_key, output, 3600)
    return output


def _normalize_search(payload: dict) -> list[dict[str, str]]:
    candidates = payload.get("data")
    if isinstance(candidates, dict):
        for key in ("results", "organic_results", "items"):
            value = candidates.get(key)
            if isinstance(value, list):
                candidates = value
                break
    if not isinstance(candidates, list):
        for key in ("results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = value
                break
    if not isinstance(candidates, list):
        return []

    output = []
    for item in candidates[:6]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "")
        url = str(item.get("url") or item.get("link") or item.get("href") or "")
        snippet = str(
            item.get("snippet")
            or item.get("description")
            or item.get("excerpt")
            or item.get("body")
            or ""
        )
        if title or url or snippet:
            output.append({"title": title[:180], "url": url[:500], "excerpt": snippet[:900]})
    return output


async def web_search(query: str, key: str) -> list[dict[str, str]]:
    """Secondary current-web search through an allowlisted RapidAPI search API."""
    query = str(query or "").strip()[:300]
    if not query or not key:
        return []
    cache_key = f"search:{query.casefold()}"
    cached = _cache_get(cache_key)
    if isinstance(cached, list):
        return cached

    payload = await _get_json(
        f"https://{SEARCH_HOST}/search",
        key,
        SEARCH_HOST,
        {"q": query, "limit": 6},
    )
    results = _normalize_search(payload)
    _cache_put(cache_key, results, 300)
    return results


async def run_tool(tool: str, value: str, key: str):
    """Run one fixed RapidAPI specialist tool."""
    if tool == "rapid_finance":
        return await finance_lookup(value, key)
    if tool == "rapid_city":
        return await city_lookup(value, key)
    if tool == "rapid_word":
        return await word_lookup(value, key)
    if tool == "rapid_search":
        return await web_search(value, key)
    raise ValueError("Unsupported RapidAPI specialist tool")
