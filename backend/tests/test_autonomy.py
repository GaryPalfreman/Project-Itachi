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

    def test_compound_finance_query_extracts_company(self):
        prompt = 'What is Microsoft trading at right now, and what was its latest trading day?'
        self.assertEqual(autonomy._clean_finance_query(prompt), 'Microsoft')
        actions = autonomy.deterministic_actions(
            prompt,
            allow_web=True,
            allow_rapidapi=True,
            limit=4,
        )
        self.assertEqual(actions[0], {'tool':'rapid_finance', 'input':'Microsoft'})

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

    async def test_verified_market_quote_bypasses_general_synthesis(self):
        live = (
            'Live market data for MSFT (Microsoft Corporation | United States | USD): '
            'price=421.77, open=418.00, high=423.00, low=417.00, volume=123456, '
            'latest_trading_day=2026-09-25, change=3.77 (0.90%).'
        )
        with patch.object(
            autonomy,
            'rapid_run_tool',
            new=AsyncMock(return_value=live),
        ), patch.object(
            autonomy,
            'search',
            new=AsyncMock(return_value=[]),
        ), patch.object(
            autonomy,
            'wikipedia',
            new=AsyncMock(return_value=[]),
        ), patch.object(
            autonomy,
            'cascade',
            new=AsyncMock(side_effect=AssertionError('general synthesis should not run')),
        ):
            answer = await autonomy.run(
                'What is Microsoft trading at right now, and what was its latest trading day?',
                [object()],
                web_key='key',
                allow_web=True,
                depth='standard',
                rapidapi_key='rapid-key',
            )
        self.assertIn('Microsoft Corporation (MSFT)', answer)
        self.assertIn('USD 421.77', answer)
        self.assertIn('2026-09-25', answer)
        self.assertNotIn("don't have access", answer.lower())

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
        results = [{'title':'Saturn', 'url':'https://example.org/saturn', 'excerpt':'Rings'}]
        with patch.object(autonomy, 'cascade', new=AsyncMock(return_value=('Answer', 'local'))), \
             patch.object(autonomy, 'search', new=AsyncMock(return_value=results)) as search:
            answer = await autonomy.run('Explain Saturn with current sources', [object()], 'key', True, depth='standard')
        self.assertEqual(answer, 'Answer')
        self.assertNotIn('https://example.org/saturn', answer)
        search.assert_awaited_once()
        query, key = search.await_args.args
        self.assertIn('Explain Saturn with current sources', query)
        self.assertEqual(key, 'key')


    def test_control_payload_detection_catches_tool_json(self):
        payload = '{"tool":"search","arguments":{"query":"NVIDIA Nemotron latest news 2026","max_results":10}}'
        self.assertTrue(autonomy.is_control_payload(payload))
        self.assertTrue(autonomy.is_control_payload('{"actions":[{"tool":"web_search","input":"x"}]}'))
        self.assertFalse(autonomy.is_control_payload('NVIDIA announced two new Nemotron developments.'))

    async def test_final_tool_json_is_retried_as_prose(self):
        results = [{'title':'Nemotron update','url':'https://example.org/nemotron','excerpt':'Fresh evidence'}]
        leaked = '{"tool":"search","arguments":{"query":"NVIDIA Nemotron latest news 2026","max_results":10}}'
        cascade = AsyncMock(side_effect=[
            (leaked, 'model-a'),
            ('Two important Nemotron developments are available in the current evidence.', 'model-b'),
        ])
        with patch.object(autonomy, 'cascade', new=cascade), \
             patch.object(autonomy, 'search', new=AsyncMock(return_value=results)):
            answer = await autonomy.run(
                'Find the latest news about NVIDIA Nemotron and summarize the two most important developments.',
                [object()],
                web_key='key',
                allow_web=True,
                depth='standard',
            )
        self.assertIn('Two important Nemotron developments', answer)
        self.assertNotIn('"tool"', answer)
        self.assertEqual(cascade.await_count, 2)

    async def test_exact_nemotron_sources_prompt_returns_prose_and_public_urls(self):
        results = [
            {
                'title': 'Nemotron release update',
                'url': 'https://example.org/nemotron-release',
                'excerpt': 'First current development',
            },
            {
                'title': 'Nemotron platform update',
                'url': 'https://example.org/nemotron-platform',
                'excerpt': 'Second current development',
            },
        ]
        leaked = '{"tool":"search","arguments":{"query":"NVIDIA Nemotron latest news 2026"}}'
        cascade = AsyncMock(side_effect=[
            (leaked, 'model-a'),
            ('The two most important developments are the release update and platform update.', 'model-b'),
        ])
        with patch.object(autonomy, 'cascade', new=cascade), \
             patch.object(autonomy, 'search', new=AsyncMock(return_value=results)):
            answer = await autonomy.run(
                'Find the latest news about NVIDIA Nemotron and summarize the two most important developments with sources.',
                [object()],
                web_key='key',
                allow_web=True,
                depth='standard',
            )
        self.assertIn('two most important developments', answer.lower())
        self.assertIn('https://example.org/nemotron-release', answer)
        self.assertIn('https://example.org/nemotron-platform', answer)
        self.assertNotIn('"tool"', answer)
        self.assertNotIn('"arguments"', answer)

    async def test_repeated_tool_json_raises_instead_of_leaking(self):
        leaked = '{"tool":"search","arguments":{"query":"NVIDIA Nemotron latest news 2026"}}'
        results = [{'title':'Nemotron update','url':'https://example.org/nemotron','excerpt':'Fresh evidence'}]
        with patch.object(autonomy, 'cascade', new=AsyncMock(return_value=(leaked, 'model'))), \
             patch.object(autonomy, 'search', new=AsyncMock(return_value=results)):
            with self.assertRaises(RuntimeError):
                await autonomy.run(
                    'Find the latest news about NVIDIA Nemotron.',
                    [object()],
                    web_key='key',
                    allow_web=True,
                    depth='standard',
                )

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
