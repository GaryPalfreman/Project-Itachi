"""Browser-context utilities for local time/date and lightweight weather.

The browser timezone is authoritative for time/date. It is only a regional hint
for location; Itachi never claims it is precise GPS data.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def normalize_timezone(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "UTC"
    candidate = value.strip()
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return "UTC"
    return candidate


def place_from_timezone(timezone_name: str) -> str:
    """Return a human-readable regional location hint from an IANA timezone."""
    timezone_name = normalize_timezone(timezone_name)
    if timezone_name == "UTC":
        return ""
    part = timezone_name.rsplit("/", 1)[-1]
    return part.replace("_", " ")


def client_context_text(timezone_name: str, locale: str = "", precise_location: bool = False) -> str:
    timezone_name = normalize_timezone(timezone_name)
    place = place_from_timezone(timezone_name)
    pieces = [f"browser timezone={timezone_name}"]
    if place:
        pieces.append(f"regional location hint={place}")
    if isinstance(locale, str) and locale.strip():
        pieces.append(f"browser locale={locale.strip()}")
    if precise_location:
        pieces.append("precise browser location permission=granted (coordinates kept session-only)")
    return "; ".join(pieces)


def local_clock_reply(prompt: str, timezone_name: str, locale: str = "", latitude: float | None = None,
                      longitude: float | None = None, accuracy_m: float | None = None) -> str | None:
    text = prompt.lower().strip()
    local_markers = ("what time", "what is the time", "what's the time", "current time", "time now",
                     "what date", "what is the date", "today's date", "todays date",
                     "what day", "date today", "where am i", "where are you")
    if not any(marker in text for marker in local_markers):
        return None

    timezone_name = normalize_timezone(timezone_name)
    now = datetime.now(timezone.utc).astimezone(ZoneInfo(timezone_name))
    place = place_from_timezone(timezone_name)

    if "where am i" in text or "where are you" in text:
        if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
            accuracy = f" (accuracy about {accuracy_m:.0f} m)" if isinstance(accuracy_m, (int, float)) else ""
            return (
                f"Your browser granted location permission. Your current coordinates are approximately "
                f"**{latitude:.5f}, {longitude:.5f}**{accuracy}. They are kept only in this session."
            )
        region = place or timezone_name
        locale_note = f" and locale {locale}" if locale else ""
        return (
            f"Your browser reports timezone **{timezone_name}**, which suggests the "
            f"regional location **{region}**{locale_note}. Precise location permission is not enabled."
        )
    if "date" in text or "what day" in text:
        return (
            f"The local date is **{now.strftime('%A, %d %B %Y')}** "
            f"in **{place or timezone_name}** ({timezone_name})."
        )
    return (
        f"The local time is **{now.strftime('%-I:%M:%S %p')}** "
        f"in **{place or timezone_name}** ({timezone_name})."
    )


def _weather_location(prompt: str, timezone_name: str) -> str:
    text = prompt.strip()
    match = re.search(r"\b(?:weather|forecast|temperature)\s+(?:in|for|at)\s+(.+?)(?:\?|$)", text, re.I)
    if match:
        explicit = match.group(1).strip(" .")
        if explicit.lower() not in {"here", "me", "my location", "my area"}:
            return explicit
    return place_from_timezone(timezone_name)


def wants_weather(prompt: str) -> bool:
    text = prompt.lower()
    return any(word in text for word in ("weather", "forecast", "temperature outside", "temperature here"))


async def weather_reply(prompt: str, timezone_name: str, locale: str = "", latitude: float | None = None,
                        longitude: float | None = None) -> str | None:
    if not wants_weather(prompt):
        return None

    location = _weather_location(prompt, normalize_timezone(timezone_name))
    inferred = place_from_timezone(normalize_timezone(timezone_name))
    explicit_location = location != inferred
    gps_available = (
        isinstance(latitude, (int, float))
        and isinstance(longitude, (int, float))
        and not explicit_location
    )
    if not location and not gps_available:
        return (
            "I can read your browser timezone, but it does not provide a usable regional "
            "location for weather. Enable precise location or ask with a city name."
        )

    language = "en"
    if isinstance(locale, str) and len(locale) >= 2:
        language = locale[:2].lower()

    first = {}
    label = "your approved location"
    async with httpx.AsyncClient(timeout=12) as client:
        if not gps_available:
            geo = await client.get(
                GEOCODING_URL,
                params={"name": location, "count": 1, "language": language, "format": "json"},
            )
            geo.raise_for_status()
            results = geo.json().get("results", [])
            if not isinstance(results, list) or not results:
                return f"I could not resolve **{location}** to a weather location."

            first = results[0]
            latitude = first.get("latitude")
            longitude = first.get("longitude")
            if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
                return f"I could not resolve coordinates for **{location}**."
            name = str(first.get("name") or location)
            admin = str(first.get("admin1") or "")
            country = str(first.get("country") or "")
            label = ", ".join(part for part in (name, admin, country) if part)

        forecast = await client.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 2,
                "timezone": "auto",
            },
        )
        forecast.raise_for_status()
        payload = forecast.json()

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    code = current.get("weather_code")
    condition = WEATHER_CODES.get(code, "current conditions unavailable")
    try:
        temp = float(current.get("temperature_2m"))
        feels = float(current.get("apparent_temperature"))
        humidity = int(current.get("relative_humidity_2m"))
        wind = float(current.get("wind_speed_10m"))
        precip = float(current.get("precipitation"))
    except (TypeError, ValueError):
        return f"Weather data for **{label}** was returned in an unexpected format."

    maxes = daily.get("temperature_2m_max") or []
    mins = daily.get("temperature_2m_min") or []
    rain_probs = daily.get("precipitation_probability_max") or []
    today = ""
    if maxes and mins:
        today = f" Today's range is about **{mins[0]}–{maxes[0]}°C**"
        if rain_probs:
            today += f" with up to **{rain_probs[0]}%** precipitation probability"
        today += "."

    if gps_available:
        regional_note = " Location came from browser permission and remains session-only."
    elif not explicit_location and inferred:
        regional_note = " Location was inferred from your browser timezone, not GPS."
    else:
        regional_note = ""

    return (
        f"Current weather for **{label}**: **{temp:.1f}°C**, {condition}; feels like "
        f"**{feels:.1f}°C**, humidity **{humidity}%**, wind **{wind:.1f} km/h**, "
        f"precipitation **{precip:.1f} mm**.{today}{regional_note}\n\n"
        "Weather data: Open-Meteo."
    )
