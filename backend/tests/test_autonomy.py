import unittest
from unittest.mock import AsyncMock, patch
from dataclasses import replace
from fastapi.testclient import TestClient

from app import autonomy, main, orchestration
from app.account_requests import prepare


class AutonomousTests(unittest.IsolatedAsyncioTestCase):
    def test_calculator_rejects_code(self):
        self.assertEqual(autonomy.calculate('(12 + 3) / 5'), 3)
        with self.assertRaises(ValueError):
            autonomy.calculate('__import__("os").system("echo unsafe")')
        with self.assertRaises(ValueError):
            autonomy.calculate('2 ** 1000')

    def test_plan_limits_and_whitelists_tools(self):
        raw = '{"actions":[{"tool":"web_search","input":"fact"},{"tool":"calculate","input":"2+2"},{"tool":"write_file","input":"x"}]}'
        self.assertEqual(autonomy.actions_from_plan(raw, False), [{'tool':'calculate','input':'2+2'}])

    def test_account_request_preparation_contacts_nothing(self):
        self.assertIn('No login was created', prepare('https://example.org/'))
        for url in ('http://example.org', 'https://127.0.0.1/',
                    'https://user:pass@example.org/', 'https://example.org/?email=a',
                    'https://localhost/', 'https://example.org/signup'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                prepare(url)

    async def test_account_request_is_explicitly_pending(self):
        plan = '{"actions":[{"tool":"request_access","input":"https://example.org/"}]}'
        with patch.object(autonomy, 'cascade', new=AsyncMock(side_effect=[(plan, 'local'), ('Response', 'local')])):
            reply = await autonomy.run('Get access', [object()])
        self.assertIn('Access requests pending review:', reply)
        self.assertIn('No login was created', reply)

    async def test_automatic_search_and_answer_without_knowledge(self):
        plan = '{"actions":[{"tool":"web_search","input":"saturn rings"}]}'
        results = [{'title':'Saturn', 'url':'https://example.org/saturn', 'excerpt':'Rings'}]
        with patch.object(autonomy, 'cascade', new=AsyncMock(side_effect=[(plan, 'local'), ('Answer', 'local')])), \
             patch.object(autonomy, 'search', new=AsyncMock(return_value=results)) as search:
            answer = await autonomy.run('Explain Saturn', [object()], 'key', True)
        self.assertIn('https://example.org/saturn', answer)
        search.assert_awaited_once_with('saturn rings', 'key')

    async def test_default_answer_does_not_read_vault(self):
        with patch.object(orchestration, 'settings', replace(orchestration.settings, knowledge_enabled=False)), \
             patch.object(orchestration.vault, 'search', side_effect=AssertionError('vault accessed')), \
             patch.object(orchestration, 'with_fallback', new=AsyncMock(return_value=('ok','primary'))):
            answer, notes = await orchestration.answer('hello')
        self.assertEqual((answer, notes), ('ok', []))


class KnowledgeAPITests(unittest.TestCase):
    def test_note_endpoints_disabled_by_default(self):
        with patch.object(main, 'settings', replace(main.settings, knowledge_enabled=False)):
            client = TestClient(main.app)
            self.assertEqual(client.get('/api/notes?q=test').status_code, 403)
            self.assertEqual(client.get('/api/note?path=foo.md').status_code, 403)
            self.assertEqual(client.post('/api/note', json={'path':'test.md','content':'test'}).status_code, 403)
