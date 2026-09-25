import unittest
from backend.app import public_knowledge
from scripts import sync_google_drive


class GoogleDriveSyncTests(unittest.TestCase):
    def test_quote_query_escapes_apostrophe_and_backslash(self):
        self.assertEqual(sync_google_drive._quote_query("Itachi's\\file"), "Itachi\\'s\\\\file")

    def test_public_knowledge_module_remains_importable(self):
        self.assertTrue(callable(public_knowledge.search))


if __name__ == "__main__":
    unittest.main()
