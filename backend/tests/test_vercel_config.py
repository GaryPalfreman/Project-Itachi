import json
import pathlib
import unittest


class VercelConfigTests(unittest.TestCase):
    def test_fastapi_entrypoint_is_not_rewritten_internally(self):
        config = json.loads(pathlib.Path("vercel.json").read_text(encoding="utf-8"))
        rewrites = config.get("rewrites", [])
        for rule in rewrites:
            destination = str(rule.get("destination", ""))
            self.assertNotIn(
                "api/index.py",
                destination,
                "Internal rewrites to the FastAPI entrypoint mutate the ASGI path on Vercel.",
            )

    def test_next_frontend_is_not_shadowed_by_catchall_backend_rewrite(self):
        config = json.loads(pathlib.Path("vercel.json").read_text(encoding="utf-8"))
        for rule in config.get("rewrites", []):
            source = str(rule.get("source", ""))
            destination = str(rule.get("destination", ""))
            self.assertFalse(
                source in {"/:path*", "/(.*)", "/(.*)*"} and destination.startswith("/api/"),
                "A catch-all backend rewrite would shadow the Next.js application.",
            )


if __name__ == "__main__":
    unittest.main()
