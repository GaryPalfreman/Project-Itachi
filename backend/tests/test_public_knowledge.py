import unittest

from backend.app.public_knowledge import context, search


class PublicKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {
                "title": "Vector embeddings",
                "url": "https://example.com/vector",
                "text": "Embeddings support semantic retrieval and vector search.",
                "source_type": "web",
                "fetched_at": "",
                "license": "TEST",
            },
            {
                "title": "Pump maintenance",
                "url": "https://example.com/pump",
                "text": "Predictive maintenance uses vibration trends for rotating equipment.",
                "source_type": "web",
                "fetched_at": "",
                "license": "TEST",
            },
        ]

    def test_search_prefers_matching_record(self):
        result = search("semantic vector retrieval", self.records, limit=1)
        self.assertEqual(result[0]["url"], "https://example.com/vector")

    def test_context_carries_provenance(self):
        rendered = context([self.records[0]])
        self.assertIn("https://example.com/vector", rendered)
        self.assertIn("Vector embeddings", rendered)

    def test_unrelated_query_returns_empty(self):
        self.assertEqual(search("astronomy telescope", self.records), [])


if __name__ == "__main__":
    unittest.main()
