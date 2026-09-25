"""Smoke coverage for the Vercel FastAPI entrypoint without external services."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api import index


class VercelAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(index.app)
        self.environment = patch.dict(os.environ, {
            "ITACHI_ACCESS_PASSCODE": "preview-passcode",
            "ITACHI_NVIDIA_API_KEY": "test-key",
        }, clear=False)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_status_health_and_unlock(self):
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["accessRequired"])
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ready"})
        self.assertEqual(self.client.post("/api/unlock", json={"passcode": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/api/unlock", json={"passcode": "preview-passcode"}).status_code, 200)

    def test_vercel_filters_local_only_model_routes(self):
        local_routes = (
            '[{"name":"local","url":"http://127.0.0.1:11434/v1",'
            '"model":"llama3.2:3b"}]'
        )
        with patch.dict(os.environ, {
            "ITACHI_MODEL_ROUTES_JSON": local_routes,
            "ITACHI_NVIDIA_API_KEY": "test-key",
        }, clear=False):
            routes = index._configured_routes()
        self.assertTrue(routes)
        self.assertTrue(all(route.url.startswith("https://") for route in routes))

    def test_local_time_is_answered_without_models(self):
        response = self.client.post("/api/chat", json={
            "prompt": "What time is it?",
            "passcode": "preview-passcode",
            "browser": {"timezone": "Australia/Melbourne", "locale": "en-AU"},
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Australia/Melbourne", response.json()["answer"])

    def test_weather_here_uses_browser_context_and_hides_backend_source_label(self):
        with patch.object(
            index,
            "weather_reply",
            new=AsyncMock(return_value="Current weather: 18.0°C, clear.\n\nWeather data: Open-Meteo."),
        ), patch.object(
            index,
            "guaranteed_answer",
            new=AsyncMock(side_effect=AssertionError("guard should not run for weather")),
        ):
            response = self.client.post("/api/chat", json={
                "prompt": "What is the weather here?",
                "passcode": "preview-passcode",
                "browser": {
                    "timezone": "Australia/Melbourne",
                    "locale": "en-AU",
                    "latitude": -37.8,
                    "longitude": 144.9,
                    "accuracy": 100,
                },
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Current weather", response.json()["answer"])
        self.assertNotIn("Open-Meteo", response.json()["answer"])

    def test_browser_coordinates_are_validated(self):
        response = self.client.post("/api/chat", json={
            "prompt": "Where am I?",
            "passcode": "preview-passcode",
            "browser": {"timezone": "UTC", "latitude": 200, "longitude": 0},
        })
        self.assertEqual(response.status_code, 422)

    def test_chat_uses_guarded_answer_and_never_returns_control_json(self):
        with patch.object(index, "guaranteed_answer", new=AsyncMock(return_value=("A safe answer", "route"))):
            response = self.client.post("/api/chat", json={
                "prompt": "Explain this",
                "passcode": "preview-passcode",
                "browser": {"timezone": "UTC"},
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "A safe answer"})

    def test_internal_failures_are_not_exposed(self):
        client = TestClient(index.app, raise_server_exceptions=False)
        with patch.object(
            index,
            "guaranteed_answer",
            new=AsyncMock(side_effect=RuntimeError("secret provider failure")),
        ):
            response = client.post("/api/chat", json={
                "prompt": "Explain this",
                "passcode": "preview-passcode",
                "browser": {"timezone": "UTC"},
            })
        self.assertEqual(response.status_code, 500)
        body = response.json()["detail"]
        self.assertIn("could not complete", body.lower())
        self.assertNotIn("provider", body.lower())
        self.assertNotIn("secret", body.lower())


if __name__ == "__main__":
    unittest.main()
