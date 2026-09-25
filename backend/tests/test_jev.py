import unittest
from unittest.mock import AsyncMock, patch

import httpx

from backend.app.jev import JevDecision, evaluate_prompt, parse_decision
from backend.app import runtime_health


class JevTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        runtime_health.reset()

    def test_parse_typed_decisions(self):
        value = parse_decision({
            "answers": {
                "route": {"type": "choice", "choice": "code"},
                "needs_web": {"type": "noul", "noul": 0.81},
                "use_learned_knowledge": {"type": "noul", "noul": 0.25},
            }
        })
        self.assertEqual(value.task, "code")
        self.assertTrue(value.needs_web)
        self.assertFalse(value.use_learned_knowledge)

    def test_parse_fails_closed_to_safe_defaults(self):
        self.assertEqual(parse_decision({}), JevDecision())

    def test_parse_malformed_route_choice_falls_back(self):
        value = parse_decision({"answers": {"route": {"choice": {"unexpected": "shape"}}}})
        self.assertEqual(value.task, "general")

    async def test_request_uses_systemone_contract_and_server_key(self):
        response = httpx.Response(
            200,
            json={
                "answers": {
                    "route": {"choice": "research"},
                    "needs_web": {"noul": 0.9},
                    "use_learned_knowledge": {"noul": 0.8},
                }
            },
            request=httpx.Request("POST", "https://api.typesafe.ai/v1/systemone"),
        )
        client = AsyncMock()
        client.post.return_value = response
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        manager.__aexit__.return_value = False

        with patch("backend.app.jev.httpx.AsyncClient", return_value=manager):
            result = await evaluate_prompt("latest release notes", "server-key")

        self.assertEqual(result.task, "research")
        args, kwargs = client.post.await_args
        self.assertEqual(args[0], "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer server-key")
        self.assertEqual(kwargs["json"]["model"], "jev-latest")
        self.assertIn("route", kwargs["json"]["questions"])


if __name__ == "__main__":
    unittest.main()
