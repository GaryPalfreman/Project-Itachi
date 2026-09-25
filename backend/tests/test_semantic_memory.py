import unittest

from backend.app.semantic_memory import (
    MemoryItem,
    SessionSemanticMemory,
    cosine_similarity,
    format_context,
)


class SemanticMemoryTests(unittest.TestCase):
    def test_cosine_similarity(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 1]), 0.0)

    def test_recall_orders_best_match(self):
        memory = SessionSemanticMemory(max_items=3)
        memory.add("boiler pressure", [1.0, 0.0], "user")
        memory.add("pump vibration", [0.8, 0.2], "assistant")
        memory.add("office lunch", [0.0, 1.0], "user")

        matches = memory.recall([1.0, 0.0], limit=2, min_similarity=0.5)

        self.assertEqual([item.text for item, _ in matches],
                         ["boiler pressure", "pump vibration"])

    def test_memory_is_bounded(self):
        memory = SessionSemanticMemory(max_items=2)
        memory.add("one", [1.0, 0.0])
        memory.add("two", [1.0, 0.0])
        memory.add("three", [1.0, 0.0])
        self.assertEqual([item.text for item in memory.items], ["two", "three"])

    def test_context_formatter(self):
        text = format_context([(MemoryItem("hello world", [1.0], "user"), 0.9)])
        self.assertIn("hello world", text)
        self.assertIn("similarity=0.900", text)


if __name__ == "__main__":
    unittest.main()
