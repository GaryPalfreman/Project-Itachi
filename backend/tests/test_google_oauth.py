import unittest
from unittest.mock import AsyncMock, patch
import httpx

from backend.app.google_oauth import (
    DEFAULT_CLIENT_ID,
    DEFAULT_REDIRECT_URI,
    authorization_url,
    exchange_code,
    oauth_config,
    issue_state,
    valid_state,
)


class GoogleOAuthTests(unittest.IsolatedAsyncioTestCase):
    def test_uploaded_web_client_shape_resolves(self):
        raw = '{"web":{"client_id":"cid","client_secret":"secret","redirect_uris":["https://project-itachi.streamlit.app"]}}'
        self.assertEqual(
            oauth_config(raw),
            ("cid", "secret", "https://project-itachi.streamlit.app"),
        )

    def test_defaults_match_deployed_itachi(self):
        client_id, secret, redirect = oauth_config(client_secret="secret")
        self.assertEqual(client_id, DEFAULT_CLIENT_ID)
        self.assertEqual(redirect, DEFAULT_REDIRECT_URI)
        self.assertEqual(secret, "secret")

    def test_state_is_signed_and_expires(self):
        state = issue_state("secret", now=1000)
        self.assertTrue(valid_state(state, "secret", now=1001))
        self.assertFalse(valid_state(state, "wrong", now=1001))
        self.assertFalse(valid_state(state, "secret", now=2000))

    def test_authorization_url_requests_offline_drive_file_access(self):
        url = authorization_url("cid", DEFAULT_REDIRECT_URI, "state", "project.itachi.storage@gmail.com")
        self.assertIn("access_type=offline", url)
        self.assertIn("prompt=consent", url)
        self.assertIn("drive.file", url)
        self.assertIn("login_hint=project.itachi.storage%40gmail.com", url)

    async def test_exchange_code_is_server_side(self):
        response = httpx.Response(
            200,
            json={"access_token":"a","refresh_token":"r","scope":"drive.file"},
            request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
        )
        client = AsyncMock()
        client.post.return_value = response
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        manager.__aexit__.return_value = False

        with patch("backend.app.google_oauth.httpx.AsyncClient", return_value=manager):
            payload = await exchange_code("code", "cid", "secret", DEFAULT_REDIRECT_URI)

        self.assertEqual(payload["refresh_token"], "r")
        _, kwargs = client.post.await_args
        self.assertEqual(kwargs["data"]["client_secret"], "secret")
        self.assertEqual(kwargs["data"]["grant_type"], "authorization_code")


if __name__ == "__main__":
    unittest.main()
