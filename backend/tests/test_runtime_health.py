import unittest
from unittest.mock import patch

import httpx

from app import runtime_health


def status_error(code: int):
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


class RuntimeHealthTests(unittest.TestCase):
    def setUp(self):
        runtime_health.reset()

    def test_success_tracks_reliability_and_latency(self):
        runtime_health.record_success("external:test", 120)
        state = runtime_health.snapshot("external:test")
        self.assertTrue(state["available"])
        self.assertEqual(state["successes"], 1)
        self.assertEqual(state["failures"], 0)
        self.assertEqual(state["latency_ema_ms"], 120)

    def test_rate_limit_opens_circuit(self):
        runtime_health.record_failure("external:test", status_error(429))
        state = runtime_health.snapshot("external:test")
        self.assertFalse(state["available"])
        self.assertGreater(state["cooldown_remaining"], 0)

    def test_auth_failure_has_longer_cooldown_than_timeout(self):
        runtime_health.record_failure("auth", status_error(401))
        auth = runtime_health.snapshot("auth")["cooldown_remaining"]
        runtime_health.record_failure("timeout", TimeoutError("slow"))
        timeout = runtime_health.snapshot("timeout")["cooldown_remaining"]
        self.assertGreater(auth, timeout)

    def test_success_closes_circuit(self):
        runtime_health.record_failure("external:test", RuntimeError("offline"))
        self.assertFalse(runtime_health.snapshot("external:test")["available"])
        runtime_health.record_success("external:test", 50)
        self.assertTrue(runtime_health.snapshot("external:test")["available"])
        self.assertEqual(runtime_health.snapshot("external:test")["consecutive_failures"], 0)


if __name__ == "__main__":
    unittest.main()
