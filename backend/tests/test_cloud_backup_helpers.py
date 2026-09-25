import unittest
import httpx
from backend.app import public_knowledge
from scripts import sync_google_drive


class GoogleDriveSyncTests(unittest.TestCase):
    def test_quote_query_escapes_apostrophe_and_backslash(self):
        self.assertEqual(sync_google_drive._quote_query("Itachi's\\file"), "Itachi\\'s\\\\file")

    def test_api_key_is_sent_in_header_not_query(self):
        seen = {}

        def respond(request):
            seen["url"] = str(request.url)
            seen["key"] = request.headers.get("x-goog-api-key")
            return httpx.Response(200, json={"files":[]}, request=request)

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            sync_google_drive.find_file(
                client,
                "public_knowledge.jsonl",
                sync_google_drive.DEFAULT_FOLDER_ID,
                "server-key",
            )

        self.assertEqual(seen["key"], "server-key")
        self.assertNotIn("server-key", seen["url"])

    def test_default_drive_folder_is_itachi_folder(self):
        self.assertEqual(
            sync_google_drive.DEFAULT_FOLDER_ID,
            "1fFi6bHUEgjU5cz9M9V8uYaNme1cGgX37",
        )

    def test_public_knowledge_module_remains_importable(self):
        self.assertTrue(callable(public_knowledge.search))


if __name__ == "__main__":
    unittest.main()
