import unittest
from unittest.mock import patch
import httpx
from app.model_catalog import ModelRoute
from app.model_selection import rank, task_for, free_hf_routes, record
from app import public_reference


class SelectionTests(unittest.IsolatedAsyncioTestCase):
    def test_task_routing_and_session_feedback(self):
        routes = [ModelRoute('general', 'https://example.org/v1', 'llama'),
                  ModelRoute('coder', 'https://example.org/v1', 'qwen-coder')]
        self.assertEqual(task_for('Write a Python function'), 'code')
        self.assertEqual(rank(routes, 'Write a Python function')[0].name, 'coder')
        feedback = {}
        for _ in range(30):
            record(feedback, 'coder', False)
            record(feedback, 'general', True)
        self.assertEqual(rank(routes, 'a general question', feedback)[0].name, 'general')
        self.assertEqual(rank(routes, 'Write a Python function', feedback)[0].name, 'general')
        self.assertNotIn('prompt', str(feedback))

    def test_rank_ignores_malformed_task_override_and_feedback(self):
        routes = [ModelRoute('general', 'https://example.org/v1', 'llama')]
        self.assertEqual(
            rank(routes, 'hello', {'general': 'bad-stats'}, task_override={'choice': 'code'})[0].name,
            'general',
        )

    def test_only_live_free_text_chat_models_discovered(self):
        catalog = {'data': [
            {'id':'org/free', 'architecture':{'output_modalities':['text']},
             'providers':[{'status':'live','is_free':True}]},
            {'id':'org/priced', 'architecture':{'output_modalities':['text']},
             'providers':[{'status':'live','is_free':False}]},
            {'id':'org/image', 'architecture':{'output_modalities':['image']},
             'providers':[{'status':'live','is_free':True}]}]}
        self.assertEqual([r.model for r in free_hf_routes(catalog, 'server-key')], ['org/free'])

    async def test_public_reference_has_useful_no_key_paths(self):
        self.assertIn('= 42', await public_reference.reply('calculate 6*7', False))
        with patch.object(public_reference, 'search_learned', return_value=[]):
            self.assertIn('Enable public reference search', await public_reference.reply('who wrote this', False))

    async def test_public_reference_search_escapes_html_and_cites_pages(self):
        def respond(request):
            self.assertEqual(request.url.host, 'en.wikipedia.org')
            self.assertIn('ProjectItachi', request.headers['User-Agent'])
            return httpx.Response(200, json={'pages':[
                {'key':'Saturn', 'title':'Saturn', 'excerpt':'A <span>ringed</span> planet'}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(public_reference.httpx, 'AsyncClient', return_value=client):
            result = await public_reference.reply('Saturn', True)
        self.assertIn('https://en.wikipedia.org/wiki/Saturn', result)
        self.assertNotIn('<span>', result)
        self.assertIn('Public reference results:', result)
        self.assertNotIn('AI answer model', result)
