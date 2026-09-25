import unittest
from unittest.mock import AsyncMock, patch
import httpx
from app import model_router

def status_error(code, body='error'):
    request = httpx.Request('POST', 'https://example.test/v1/chat/completions')
    response = httpx.Response(code, text=body, request=request)
    return httpx.HTTPStatusError(body, request=request, response=response)

class RouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_quota_uses_one_fallback(self):
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=[status_error(429), 'answer'])) as run:
            result = await model_router.with_fallback(('p','m',''), ('f','llama',''), [])
            self.assertEqual(result, ('answer','fallback'))
            self.assertEqual(run.await_count, 2)

    async def test_invalid_credentials_never_fall_back(self):
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=status_error(401))) as run:
            with self.assertRaises(httpx.HTTPStatusError):
                await model_router.with_fallback(('p','m',''), ('f','llama',''), [])
            self.assertEqual(run.await_count, 1)

    async def test_context_error_uses_fallback(self):
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=[status_error(400,'context length exceeded'), 'ok'])):
            self.assertEqual((await model_router.with_fallback(('p','m',''), ('f','llama',''), []))[1], 'fallback')

    async def test_no_config_never_loops(self):
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=httpx.ConnectError('offline'))) as run:
            with self.assertRaises(httpx.ConnectError):
                await model_router.with_fallback(('p','m',''), ('','',''), [])
            self.assertEqual(run.await_count, 1)
