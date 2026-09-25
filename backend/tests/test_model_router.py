import unittest
from unittest.mock import AsyncMock, patch
import httpx
from app import model_router, runtime_health
from app.model_catalog import ModelRoute

def status_error(code, body='error'):
    request = httpx.Request('POST', 'https://example.test/v1/chat/completions')
    response = httpx.Response(code, text=body, request=request)
    return httpx.HTTPStatusError(body, request=request, response=response)

class RouterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        runtime_health.reset()

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

    async def test_cascade_quarantines_bad_auth_route_and_uses_next(self):
        routes = [
            ModelRoute('bad', 'https://bad.example/v1', 'bad-model', 'bad-key'),
            ModelRoute('good', 'https://good.example/v1', 'good-model', 'good-key'),
        ]
        with patch.object(
            model_router,
            'completion',
            new=AsyncMock(side_effect=[status_error(401), 'answer']),
        ) as run:
            answer, route = await model_router.cascade(routes, [])
        self.assertEqual((answer, route), ('answer', 'good'))
        self.assertEqual(run.await_count, 2)
        self.assertFalse(runtime_health.snapshot('model:bad')['available'])

    async def test_cascade_records_latency_and_success(self):
        routes = [ModelRoute('good', 'https://good.example/v1', 'good-model', 'key')]
        with patch.object(model_router, 'completion', new=AsyncMock(return_value='ok')):
            self.assertEqual(await model_router.cascade(routes, []), ('ok', 'good'))
        health = runtime_health.snapshot('model:good')
        self.assertEqual(health['successes'], 1)
        self.assertGreaterEqual(health['latency_ema_ms'], 0)

    async def test_context_error_uses_fallback(self):
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=[status_error(400,'context length exceeded'), 'ok'])):
            self.assertEqual((await model_router.with_fallback(('p','m',''), ('f','llama',''), []))[1], 'fallback')

    async def test_no_config_never_loops(self):
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=httpx.ConnectError('offline'))) as run:
            with self.assertRaises(httpx.ConnectError):
                await model_router.with_fallback(('p','m',''), ('','',''), [])
            self.assertEqual(run.await_count, 1)
