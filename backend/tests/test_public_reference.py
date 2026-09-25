import unittest
from unittest.mock import AsyncMock, patch

from app import public_reference


class PublicReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_request_skips_stale_learned_corpus(self):
        stale = [{
            "title": "Old Nemotron note",
            "url": "https://old.example/nemotron",
            "text": "stale",
            "source_type": "web",
            "fetched_at": "2020-01-01T00:00:00+00:00",
            "license": "TEST",
        }]
        fresh = [{
            "title": "Current Nemotron update",
            "url": "https://example.org/current",
            "excerpt": "Current release details",
        }]
        with patch.object(public_reference, "search_learned", return_value=stale) as learned, \
             patch.object(public_reference, "wikipedia", new=AsyncMock(return_value=fresh)):
            answer = await public_reference.reply(
                "Find the latest Nemotron news with sources",
                True,
            )
        learned.assert_not_called()
        self.assertIn("https://example.org/current", answer)
        self.assertNotIn("old.example", answer)

    async def test_timeless_request_can_use_learned_corpus(self):
        learned_item = [{
            "title": "Recursion",
            "url": "https://example.org/recursion",
            "text": "Recursion is a self-referential technique.",
            "source_type": "web",
            "fetched_at": "2026-09-01T00:00:00+00:00",
            "license": "TEST",
        }]
        with patch.object(public_reference, "search_learned", return_value=learned_item):
            answer = await public_reference.reply("Explain recursion", True)
        self.assertIn("Itachi learned public references", answer)


if __name__ == "__main__":
    unittest.main()
