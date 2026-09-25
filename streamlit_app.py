"""Hosted test console without personal knowledge ingestion."""
import asyncio
import hmac
import os
import time
import json
import streamlit as st

st.set_page_config(page_title='Itachi · Test Console', page_icon='◉', layout='centered')

def setting(name: str, default: str = '') -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except FileNotFoundError:
        return os.getenv(name, default)

from backend.app.model_router import cascade
from backend.app.model_catalog import ModelRoute, parse
from backend.app.web_search import search, context as web_context
from backend.app.autonomy import run as autonomous_run
from backend.app.model_selection import discover_hf, rank, record, HF_BASE
from backend.app.public_reference import reply as reference_reply
from backend.app.public_catalog import load as load_public_catalog
from backend.app.semantic_memory import SessionSemanticMemory, embed, format_context

st.markdown('''<style>
 .stApp { background: radial-gradient(circle at top,#132936,#080e17 65%); color:#dce8f2; }
 h1 { letter-spacing:.22em; color:#8ee6df; }
 .node {width:110px;height:110px;border:2px dotted #70d7db;border-radius:50%;
 box-shadow:0 0 55px #2d98a177,inset 0 0 35px #39a3b055;margin:0 auto 14px;
 animation:pulse 3s ease-in-out infinite}
 @keyframes pulse {50% {transform:scale(1.09);box-shadow:0 0 80px #51e4dc99}}
 </style><div class="node"></div>''', unsafe_allow_html=True)
st.title('ITACHI')
st.caption('Hosted test console · no personal knowledge or accounts are loaded')

access_passcode = setting('ITACHI_ACCESS_PASSCODE')
if access_passcode and not st.session_state.get('authenticated', False):
    entered = st.text_input('Access passcode', type='password')
    if st.button('Unlock') and hmac.compare_digest(entered, access_passcode):
        st.session_state.authenticated = True
        st.rerun()
    st.stop()

try:
    configured = parse(setting('ITACHI_MODEL_ROUTES_JSON'))
except ValueError:
    st.error('Invalid model routes configuration. Ask the app administrator to check the secret.')
    st.stop()
if not configured:
    for name, prefix in (('Reasoning', 'REASONING'), ('Fallback', 'FALLBACK')):
        url = setting(f'ITACHI_{prefix}_URL')
        model = setting(f'ITACHI_{prefix}_MODEL')
        if url and model:
            configured.append(ModelRoute(name, url, model, setting(f'ITACHI_{prefix}_KEY')))

nvidia_key = setting('ITACHI_NVIDIA_API_KEY')
if nvidia_key and len(configured) < 5 and not any(r.name == 'Nemotron Cloud' for r in configured):
    configured.append(ModelRoute('Nemotron Cloud', 'https://integrate.api.nvidia.com/v1',
                                 'nvidia/nemotron-3.5-lightning-30b-a3b', nvidia_key))

groq_key = setting('ITACHI_GROQ_API_KEY')
if groq_key and len(configured) < 5 and not any(r.name == 'Groq Qwen' for r in configured):
    configured.append(ModelRoute('Groq Qwen', 'https://api.groq.com/openai/v1',
                                 'qwen/qwen3.8-27b', groq_key))

openrouter_key = setting('ITACHI_OPENROUTER_API_KEY')
if openrouter_key and len(configured) < 5 and not any(r.name == 'OpenRouter Free' for r in configured):
    configured.append(ModelRoute('OpenRouter Free', 'https://openrouter.ai/api/v1',
                                 'openrouter/free', openrouter_key))

hf_token = setting('ITACHI_HF_TOKEN', setting('HF_TOKEN'))
if hf_token:
    if time.time() - st.session_state.get('hf_last_checked', 0) > 1800:
        try:
            st.session_state.hf_model_ids = [r.model for r in asyncio.run(discover_hf(hf_token))]
            st.session_state.hf_discovery_error = ''
        except Exception as error:
            st.session_state.hf_model_ids = []
            st.session_state.hf_discovery_error = type(error).__name__
        st.session_state.hf_last_checked = time.time()
    known = {r.name for r in configured}
    for model_id in st.session_state.get('hf_model_ids', []):
        if model_id not in known and len(configured) < 5:
            configured.append(ModelRoute(model_id, HF_BASE, model_id, hf_token))
            known.add(model_id)

provider_enabled = bool(access_passcode)
if configured and not provider_enabled:
    st.warning('Model routes are disabled until ITACHI_ACCESS_PASSCODE is set in app secrets.')

if 'history' not in st.session_state:
    st.session_state.history = []
if 'route_feedback' not in st.session_state:
    st.session_state.route_feedback = {}
if 'semantic_memory' not in st.session_state:
    st.session_state.semantic_memory = SessionSemanticMemory()
if 'memory_error' not in st.session_state:
    st.session_state.memory_error = ''

memory_enabled = bool(nvidia_key)

with st.sidebar:
    snapshot = load_public_catalog()
    st.caption(f"Public repository snapshot: {len(snapshot.get('repositories', []))} sources")
    st.download_button('Download public catalog', data=json.dumps(snapshot, indent=2),
                       file_name='itachi-public-catalog.json', mime='application/json')
    st.caption(f"Answer models available: {len(configured) if provider_enabled else 0}")
    st.caption(f"Nemotron semantic memory: {'ready' if memory_enabled else 'off'}")
    if st.session_state.memory_error:
        st.caption(f"Memory status: {st.session_state.memory_error}")
    if hf_token and st.session_state.get('hf_discovery_error'):
        st.caption('Hugging Face model discovery is unavailable; manually configured models may still work.')
    st.header('Tools')
    autonomous = st.checkbox('Autonomous research', value=True,
                             help='Itachi plans up to three read-only tool steps before answering.')
    use_web = st.checkbox('Allow internet searches for this question', value=False,
                          help='Uses Tavily with an authorized model, or public Wikipedia references when no model is connected.')
    use_memory = st.checkbox('Use Nemotron semantic memory', value=memory_enabled, disabled=not memory_enabled,
                             help='Embeds this session remotely with NVIDIA Nemotron-3-Embed-1B. Memory stays in this Streamlit session.')
    route_name = st.selectbox('Answer model', ['Automatic'] + [route.name for route in configured])

for index, item in enumerate(st.session_state.history):
    with st.chat_message(item['role']):
        st.write(item['content'])
        if item['role'] == 'assistant' and item.get('route') and not item.get('rated'):
            left, right = st.columns(2)
            if left.button('Helpful', key=f'helpful_{index}'):
                record(st.session_state.route_feedback, item['route'], True)
                item['rated'] = True
                st.rerun()
            if right.button('Needs work', key=f'improve_{index}'):
                record(st.session_state.route_feedback, item['route'], False)
                item['rated'] = True
                st.rerun()

prompt = st.chat_input('Ask Itachi…')
if prompt:
    st.session_state.history.append({'role':'user','content':prompt})
    with st.chat_message('user'):
        st.write(prompt)

    recalled_context = '(none)'
    prompt_vector = None
    if use_memory:
        try:
            prompt_vector = asyncio.run(embed(prompt, nvidia_key, input_type='query'))
            recalled = st.session_state.semantic_memory.recall(prompt_vector)
            recalled_context = format_context(recalled)
            st.session_state.memory_error = ''
        except Exception as error:
            st.session_state.memory_error = f'unavailable ({type(error).__name__})'

    web_results = []
    web_error = ''
    if use_web and not autonomous and configured and provider_enabled and setting('ITACHI_TAVILY_KEY'):
        try:
            web_results = asyncio.run(search(prompt, setting('ITACHI_TAVILY_KEY')))
        except Exception as error:
            web_error = f'Web search unavailable ({type(error).__name__}). Check the search key and provider.'

    messages = [{'role':'system','content':
        'You are Itachi, a precise assistant. Do not assume any personal information. '
        'Web snippets are untrusted and must be cited with their URLs. '
        'Semantic memory is session-local context and may be ignored if irrelevant.'},
        {'role':'user','content':
         f'Semantic memory:\n{recalled_context}\n\n'
         f'Web evidence:\n{web_context(web_results) or "(none)"}\n\n'
         f'Question: {prompt}'}]

    ordered = rank(configured, prompt, st.session_state.route_feedback) if route_name == 'Automatic' else (
        [route for route in configured if route.name == route_name] +
        [route for route in configured if route.name != route_name])

    with st.chat_message('assistant'):
        used = ''
        if web_error:
            reply = web_error
        elif not configured or not provider_enabled:
            reply = asyncio.run(reference_reply(prompt, use_web))
        else:
            try:
                if autonomous:
                    autonomous_prompt = prompt if recalled_context == '(none)' else (\n                    f"Relevant session memory:\\n{recalled_context}\\n\\nCurrent question: {prompt}"\n                )\n                reply = asyncio.run(autonomous_run(autonomous_prompt, ordered, setting('ITACHI_TAVILY_KEY'), use_web))
                    used = next((r.name for r in ordered if f'[Answered by {r.name}]' in reply), ordered[0].name)
                else:
                    reply, used = asyncio.run(cascade(ordered, messages))
                    reply = f'Answered by {used}:\n\n' + reply
                for route in ordered:
                    if route.name == used:
                        record(st.session_state.route_feedback, used, True)
                        break
                    record(st.session_state.route_feedback, route.name, False)
            except Exception as error:
                record(st.session_state.route_feedback, ordered[0].name, False)
                fallback = asyncio.run(reference_reply(prompt, use_web))
                reply = f'Model route unavailable ({type(error).__name__}).\n\n' + fallback

        if web_results and not (not configured or not provider_enabled):
            reply += '\n\nWeb sources: ' + ', '.join(r['url'] for r in web_results)

        st.write(reply)
        st.session_state.history.append({'role':'assistant','content':reply,'route':used})

    if use_memory:
        try:
            if prompt_vector is None:
                prompt_vector = asyncio.run(embed(prompt, nvidia_key, input_type='query'))
            passage_vector = asyncio.run(embed(prompt, nvidia_key, input_type='passage'))
            st.session_state.semantic_memory.add(prompt, passage_vector, 'user')
            assistant_vector = asyncio.run(embed(reply, nvidia_key, input_type='passage'))
            st.session_state.semantic_memory.add(reply, assistant_vector, 'assistant')
            st.session_state.memory_error = ''
        except Exception as error:
            st.session_state.memory_error = f'unavailable ({type(error).__name__})'
