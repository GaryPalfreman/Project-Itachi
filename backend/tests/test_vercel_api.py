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

    def test_local_time_is_answered_without_models(self):
        response = self.client.post("/api/chat", json={
            "prompt": "What time is it?",
            "passcode": "preview-passcode",
            "browser": {"timezone": "Australia/Melbourne", "locale": "en-AU"},
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Australia/Melbourne", response.json()["answer"])

    def test_chat_uses_guarded_answer_and_never_returns_control_json(self):
        with patch.object(index, "guaranteed_answer", new=AsyncMock(return_value=("A safe answer", "route"))):
            response = self.client.post("/api/chat", json={
                "prompt": "Explain this",
                "passcode": "preview-passcode",
                "browser": {"timezone": "UTC"},
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "A safe answer"})


if __name__ == "__main__":
    unittest.main()
