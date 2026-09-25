import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend.app.client_context import (
    client_context_text,
    local_clock_reply,
    normalize_timezone,
    place_from_timezone,
    weather_reply,
)


class ClientContextTests(unittest.IsolatedAsyncioTestCase):
    def test_timezone_is_browser_region_not_gps(self):
        self.assertEqual(normalize_timezone("Australia/Melbourne"), "Australia/Melbourne")
        self.assertEqual(place_from_timezone("Australia/Melbourne"), "Melbourne")
        text = client_context_text("Australia/Melbourne", "en-AU")
        self.assertIn("browser timezone=Australia/Melbourne", text)
        self.assertIn("browser locale=en-AU", text)

    def test_invalid_timezone_falls_back_to_utc(self):
        self.assertEqual(normalize_timezone({"bad": "shape"}), "UTC")
        self.assertEqual(normalize_timezone("Not/AZone"), "UTC")

    def test_clock_reply_uses_timezone(self):
        reply = local_clock_reply("what is the time?", "Australia/Melbourne", "en-AU")
        self.assertIn("Australia/Melbourne", reply)
        self.assertIn("Melbourne", reply)

    async def test_weather_uses_timezone_city_and_open_meteo(self):
        geo_response = httpx.Response(
            200,
            json={"results": [{
                "name": "Melbourne", "admin1": "Victoria", "country": "Australia",
                "latitude": -37.81, "longitude": 144.96
            }]},
            request=httpx.Request("GET", "https://geocoding-api.open-meteo.com/v1/search"),
        )
        weather_response = httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 18.2,
                    "apparent_temperature": 17.4,
                    "relative_humidity_2m": 62,
                    "precipitation": 0.0,
                    "weather_code": 2,
                    "wind_speed_10m": 12.5,
                },
                "daily": {
                    "temperature_2m_max": [20.0, 22.0],
                    "temperature_2m_min": [10.0, 11.0],
                    "precipitation_probability_max": [15, 10],
                },
            },
            request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"),
        )
        client = AsyncMock()
        client.get.side_effect = [geo_response, weather_response]
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        manager.__aexit__.return_value = False

        with patch("backend.app.client_context.httpx.AsyncClient", return_value=manager):
            reply = await weather_reply("what is the weather here?", "Australia/Melbourne", "en-AU")

        self.assertIn("Melbourne, Victoria, Australia", reply)
        self.assertIn("18.2°C", reply)
        self.assertIn("not GPS", reply)
        self.assertIn("Open-Meteo", reply)


if __name__ == "__main__":
    unittest.main()
