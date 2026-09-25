import unittest
from unittest.mock import AsyncMock, patch

from app import answer_guard


class AnswerGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_primary_autonomy_answer_is_used(self):
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(return_value=('Primary answer', 'route-a')),
        ):
            answer, route = await answer_guard.guaranteed_answer('hello', [object()])
        self.assertEqual(answer, 'Primary answer')
        self.assertEqual(route, 'route-a')

    async def test_empty_primary_falls_back_to_direct_model(self):
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(return_value=('', '')),
        ), patch.object(
            answer_guard,
            'cascade',
            new=AsyncMock(return_value=('Fallback answer', 'route-b')),
        ):
            answer, route = await answer_guard.guaranteed_answer('hello', [object()])
        self.assertEqual(answer, 'Fallback answer')
        self.assertEqual(route, 'route-b')

    async def test_all_model_failures_still_return_public_reference(self):
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(side_effect=RuntimeError('down')),
        ), patch.object(
            answer_guard,
            'cascade',
            new=AsyncMock(side_effect=RuntimeError('down')),
        ), patch.object(
            answer_guard,
            'reference_reply',
            new=AsyncMock(return_value='Reference answer'),
        ):
            answer, route = await answer_guard.guaranteed_answer('hello', [object()])
        self.assertEqual(answer, 'Reference answer')
        self.assertEqual(route, '')

    async def test_rapidapi_search_is_secondary_web_fallback(self):
        results = [{'title':'Current result','url':'https://example.org','excerpt':'fresh'}]
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(side_effect=RuntimeError('planner down')),
        ), patch.object(
            answer_guard,
            'rapid_web_search',
            new=AsyncMock(return_value=results),
        ) as rapid_search, patch.object(
            answer_guard,
            'cascade',
            new=AsyncMock(return_value=('Direct answer', 'route')),
        ):
            answer, _ = await answer_guard.guaranteed_answer(
                'latest result',
                [object()],
                allow_web=True,
                rapidapi_key='rapid-key',
            )
        self.assertIn('Direct answer', answer)
        self.assertNotIn('https://example.org', answer)
        rapid_search.assert_awaited_once()

    async def test_source_footer_is_hidden_unless_requested(self):
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(return_value=('Useful answer\n\nSource: WordsAPI https://rapidapi.com/example', 'route')),
        ):
            answer, _ = await answer_guard.guaranteed_answer('define resilient', [object()])
            sourced, _ = await answer_guard.guaranteed_answer(
                'define resilient and show your sources',
                [object()],
            )
        self.assertEqual(answer, 'Useful answer')
        self.assertIn('Source:', sourced)

    async def test_primary_tool_json_is_not_returned_to_user(self):
        leaked = '{"tool":"search","arguments":{"query":"NVIDIA Nemotron latest news 2026","max_results":10}}'
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(return_value=(leaked, 'route-a')),
        ), patch.object(
            answer_guard,
            'cascade',
            new=AsyncMock(return_value=('Final prose answer', 'route-b')),
        ):
            answer, route = await answer_guard.guaranteed_answer(
                'Find the latest news about NVIDIA Nemotron.',
                [object()],
            )
        self.assertEqual(answer, 'Final prose answer')
        self.assertEqual(route, 'route-b')
        self.assertNotIn('"tool"', answer)

    async def test_fallback_tool_json_retries_once(self):
        leaked = '{"tool":"search","arguments":{"query":"NVIDIA Nemotron latest news 2026"}}'
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(side_effect=RuntimeError('primary down')),
        ), patch.object(
            answer_guard,
            'cascade',
            new=AsyncMock(side_effect=[
                (leaked, 'route-a'),
                ('Recovered final prose', 'route-b'),
            ]),
        ):
            answer, route = await answer_guard.guaranteed_answer(
                'Find the latest news about NVIDIA Nemotron.',
                [object()],
            )
        self.assertEqual(answer, 'Recovered final prose')
        self.assertEqual(route, 'route-b')

    async def test_final_failure_does_not_expose_internal_exception_type(self):
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(side_effect=RuntimeError('provider secret detail')),
        ), patch.object(
            answer_guard,
            'reference_reply',
            new=AsyncMock(return_value=''),
        ):
            answer, _ = await answer_guard.guaranteed_answer('hello', [])
        self.assertNotIn('RuntimeError', answer)
        self.assertNotIn('provider', answer.lower())
        self.assertTrue(answer.strip())

    async def test_exhausted_budget_returns_without_starting_fallback_work(self):
        with patch.object(answer_guard, '_timeout_for', return_value=0), \
             patch.object(
                 answer_guard,
                 'autonomous_run',
                 new=AsyncMock(side_effect=AssertionError('primary should not start')),
             ) as primary, \
             patch.object(
                 answer_guard,
                 'reference_reply',
                 new=AsyncMock(side_effect=AssertionError('fallback should not start')),
             ) as reference:
            answer, _ = await answer_guard.guaranteed_answer('hello', [])
        primary.assert_not_awaited()
        reference.assert_not_awaited()
        self.assertTrue(answer.strip())

    async def test_guard_never_returns_empty_text(self):
        with patch.object(
            answer_guard,
            'autonomous_run',
            new=AsyncMock(return_value=('', '')),
        ), patch.object(
            answer_guard,
            'reference_reply',
            new=AsyncMock(return_value=''),
        ):
            answer, _ = await answer_guard.guaranteed_answer('hello', [])
        self.assertTrue(answer.strip())


if __name__ == '__main__':
    unittest.main()
