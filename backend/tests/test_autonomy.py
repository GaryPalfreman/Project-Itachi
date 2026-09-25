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

    def test_depth_selection(self):
        self.assertEqual(autonomy.depth_for('hello there'), 'quick')
        self.assertEqual(autonomy.depth_for('Please do a comprehensive architecture comparison'), 'deep')
        self.assertEqual(autonomy.depth_for('Explain caching with a few examples'), 'standard')
        self.assertEqual(autonomy.depth_for('hello', 'deep'), 'deep')

    def test_current_result_questions_force_fresh_web(self):
        self.assertTrue(autonomy.requires_fresh_web('Who won the last FIFA World Cup?'))
        self.assertTrue(autonomy.requires_fresh_web('What is the latest Python release?'))
        self.assertFalse(autonomy.requires_fresh_web('Explain recursion'))

    def test_rapidapi_tools_are_only_allowed_when_configured(self):
        raw = '{"actions":[{"tool":"rapid_finance","input":"MSFT"},{"tool":"rapid_city","input":"Melbourne"}]}'
        self.assertEqual(autonomy.actions_from_plan(raw, True), [])
        allowed = autonomy.actions_from_plan(raw, True, allow_rapidapi=True)
        self.assertEqual([item['tool'] for item in allowed], ['rapid_finance', 'rapid_city'])

    def test_deterministic_multi_question_specialist_routing(self):
        prompt = (
            'What is Microsoft trading at right now?\n'
            'Give me structured information about Melbourne, Australia.\n'
            'Define ephemeral and give me synonyms.\n'
            'Find the latest news about NVIDIA Nemotron.'
        )
        actions = autonomy.deterministic_actions(
            prompt,
            allow_web=True,
            allow_rapidapi=True,
            limit=4,
        )
        self.assertEqual(
            [item['tool'] for item in actions],
            ['rapid_finance', 'rapid_city', 'rapid_word', 'web_search'],
        )
        self.assertEqual(actions[0]['input'], 'Microsoft')
        self.assertEqual(actions[1]['input'], 'Melbourne, Australia')
        self.assertEqual(actions[2]['input'], 'ephemeral')

    def test_plan_honors_deep_action_limit(self):
        raw = '{"actions":[' + ','.join(
            '{"tool":"calculate","input":"2+2"}' for _ in range(6)
        ) + ']}'
        self.assertEqual(len(autonomy.actions_from_plan(raw, False, 5)), 5)

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
            reply = await autonomy.run('Get access now with a public account request', [object()], depth='standard')
        self.assertIn('Access requests pending review:', reply)
        self.assertIn('No login was created', reply)

    async def test_standard_deterministic_route_skips_planner(self):
        with patch.object(
            autonomy,
            'rapid_run_tool',
            new=AsyncMock(return_value='price=500'),
        ) as rapid, patch.object(
            autonomy,
            'cascade',
            new=AsyncMock(return_value=('Answer', 'model')),
        ) as cascade:
            answer = await autonomy.run(
                'What is Microsoft trading at right now?',
                [object()],
                allow_web=True,
                depth='standard',
                rapidapi_key='key',
            )
        self.assertIn('Answer', answer)
        rapid.assert_awaited_once_with('rapid_finance', 'Microsoft', 'key')
        self.assertEqual(cascade.await_count, 1)

    async def test_deep_mode_keeps_planner_with_rapidapi_specialist(self):
        plan = '{"actions":[{"tool":"rapid_finance","input":"Microsoft"}]}'
        cascade = AsyncMock(side_effect=[
            (plan, 'planner'),
            ('Draft', 'model'),
            ('Critique', 'critic'),
            ('Answer', 'model'),
        ])
        with patch.object(autonomy, 'cascade', new=cascade), \
             patch.object(autonomy, 'rapid_run_tool', new=AsyncMock(return_value='price=500')) as rapid:
            answer = await autonomy.run(
                'What is Microsoft stock trading at?',
                [object()],
                allow_web=True,
                depth='deep',
                rapidapi_key='key',
            )
        self.assertIn('Answer', answer)
        rapid.assert_awaited_once_with('rapid_finance', 'Microsoft', 'key')
        self.assertEqual(cascade.await_count, 4)

    async def test_automatic_search_and_answer_without_knowledge(self):
        plan = '{"actions":[{"tool":"web_search","input":"saturn rings"}]}'
        results = [{'title':'Saturn', 'url':'https://example.org/saturn', 'excerpt':'Rings'}]
        with patch.object(autonomy, 'cascade', new=AsyncMock(side_effect=[(plan, 'local'), ('Answer', 'local')])), \
             patch.object(autonomy, 'search', new=AsyncMock(return_value=results)) as search:
            answer = await autonomy.run('Explain Saturn with current sources', [object()], 'key', True, depth='standard')
        self.assertIn('https://example.org/saturn', answer)
        search.assert_awaited_once()
        query, key = search.await_args.args
        self.assertIn('Explain Saturn with current sources', query)
        self.assertEqual(key, 'key')


    async def test_deep_mode_adds_critique_and_revision(self):
        plan = '{"actions":[]}'
        cascade = AsyncMock(side_effect=[
            (plan, 'planner'),
            ('Draft', 'model-a'),
            ('Fix unsupported claim', 'critic'),
            ('Revised answer', 'model-b'),
        ])
        with patch.object(autonomy, 'cascade', new=cascade):
            answer = await autonomy.run(
                'Give a comprehensive analysis of this architecture',
                [object()],
                depth='deep',
            )
        self.assertIn('Revised answer', answer)
        self.assertEqual(cascade.await_count, 4)

    async def test_provider_identity_is_not_exposed(self):
        cascade = AsyncMock(side_effect=[
            ('Direct answer', 'NVIDIA Nemotron Ultra'),
            ('Direct answer', 'NVIDIA Nemotron Ultra'),
        ])
        with patch.object(autonomy, 'cascade', new=cascade):
            answer = await autonomy.run('hello there', [object()], depth='quick')
            answer_with_route, route = await autonomy.run(
                'hello there',
                [object()],
                depth='quick',
                return_route=True,
            )
        self.assertEqual(answer, 'Direct answer')
        self.assertEqual(answer_with_route, 'Direct answer')
        self.assertEqual(route, 'NVIDIA Nemotron Ultra')
        self.assertNotIn('Answered by', answer)

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
