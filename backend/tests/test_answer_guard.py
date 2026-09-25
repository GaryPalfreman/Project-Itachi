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
