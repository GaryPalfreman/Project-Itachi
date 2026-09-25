import unittest
import json
from unittest.mock import AsyncMock, patch
import httpx
from app import github_public, autonomy
from app.public_catalog import load
from scripts import refresh_public_catalog
from app import mirrors


class PublicCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_github_search_fetches_metadata_without_cloning(self):
        def reply(request):
            self.assertEqual(request.url.path, '/search/repositories')
            return httpx.Response(200, json={'items':[
                {'full_name':'example/open', 'description':'Library', 'license':{'spdx_id':'MIT'},
                 'stargazers_count':100, 'pushed_at':'2026-09-01T00:00:00Z'}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(reply))
        with patch.object(github_public.httpx, 'AsyncClient', return_value=client):
            result = await github_public.search_repos('python package')
        self.assertEqual(result[0]['url'], 'https://github.com/example/open')
        self.assertEqual(result[0]['license'], 'MIT')
        self.assertNotIn('source_code', result[0])

    async def test_autonomous_research_uses_github_without_tavily_key(self):
        plan = '{"actions":[{"tool":"github_search","input":"fastapi plugins"}]}'
        item = {'name':'example/open', 'url':'https://github.com/example/open',
                'license':'MIT','description':'Library'}
        with patch.object(autonomy, 'cascade', new=AsyncMock(side_effect=[(plan,'a'),('Answer','a')])), \
             patch.object(autonomy, 'search_repos', new=AsyncMock(return_value=[item])):
            output = await autonomy.run('Find open source code', [object()], allow_web=True)
        self.assertEqual(output, 'Answer')
        self.assertNotIn('https://github.com/example/open', output)

    async def test_refresh_is_allowlisted_and_metadata_only(self):
        with patch.object(refresh_public_catalog, 'catalog_repos',
                          new=AsyncMock(return_value=[{'name':'example/open'}])) as repos, \
             patch.object(refresh_public_catalog, 'wikipedia', new=AsyncMock(return_value=[])):
            result = await refresh_public_catalog.refresh()
        self.assertTrue(all('/' in name for name in repos.await_args.args[0]))
        self.assertEqual(result['repositories'], [{'name':'example/open'}])

    def test_checked_in_snapshot_is_public_metadata(self):
        snapshot = load()
        self.assertGreater(len(snapshot['repositories']), 0)
        for item in snapshot['repositories']:
            self.assertTrue(item['url'].startswith('https://github.com/'))
            self.assertNotIn('token', item)

    def test_mirrors_reject_internal_and_unsigned_targets(self):
        for target in ('http://example.com/catalog.json', 'https://127.0.0.1/catalog.json',
                       'https://example.com/catalog.json?sig=secret'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                mirrors.parse(json.dumps([{'name':'backup','url':target,
                                           'token_env':'ITACHI_MIRROR_TOKEN_1'}]))

    async def test_mirror_uses_server_side_token_only(self):
        def reply(request):
            self.assertEqual(request.headers['Authorization'], 'Bearer secret-test')
            self.assertEqual(request.content, b'{"repositories":[]}')
            return httpx.Response(200)
        routes = mirrors.parse(json.dumps([{'name':'backup',
            'url':'https://storage.example/catalog.json','token_env':'ITACHI_MIRROR_TOKEN_1'}]))
        client = httpx.AsyncClient(transport=httpx.MockTransport(reply))
        with patch.object(mirrors.httpx, 'AsyncClient', return_value=client):
            updated = await mirrors.upload(b'{"repositories":[]}', routes,
                                           {'ITACHI_MIRROR_TOKEN_1':'secret-test'})
        self.assertEqual(updated, ['backup'])
