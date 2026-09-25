import json
import unittest
from unittest.mock import AsyncMock, patch
import httpx

from app.model_catalog import parse
from app import model_router, web_search


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def test_model_catalog_rejects_public_plaintext_and_url_credentials(self):
        for url in ('http://example.com/v1', 'https://user:pass@example.com/v1',
                    'https://example.com/v1?key=abc', 'https://example.com/v1/chat/completions'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse(json.dumps([{'name':'x', 'url':url, 'model':'m'}]))

    async def test_cascade_quota_then_local_model(self):
        routes = parse(json.dumps([
            {'name':'cloud', 'url':'https://example.com/v1', 'model':'cloud-model'},
            {'name':'ollama', 'url':'http://127.0.0.1:11434/v1', 'model':'llama3.2:3b'}]))
        request = httpx.Request('POST', 'https://example.com/v1/chat/completions')
        response = httpx.Response(429, request=request)
        unavailable = httpx.HTTPStatusError('quota', request=request, response=response)
        with patch.object(model_router, 'completion', new=AsyncMock(side_effect=[unavailable, 'ok'])) as call:
            self.assertEqual(await model_router.cascade(routes, []), ('ok', 'ollama'))
            self.assertEqual(call.await_count, 2)

    async def test_search_sends_only_query_and_returns_sources(self):
        def respond(request):
            payload = json.loads(request.content)
            self.assertEqual(payload['query'], 'pump efficiency')
            self.assertNotIn('vault', payload)
            return httpx.Response(200, json={'results':[
                {'title':'Reference', 'url':'https://example.com/a', 'content':'Excerpt'}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(web_search.httpx, 'AsyncClient', return_value=client):
            results = await web_search.search('pump efficiency', 'test-key')
        self.assertEqual(results[0]['url'], 'https://example.com/a')
