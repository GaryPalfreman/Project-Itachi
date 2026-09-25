"""Hosted test console without personal knowledge ingestion."""
import asyncio
import hmac
import os
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

provider_enabled = bool(access_passcode)
if configured and not provider_enabled:
    st.warning('Model routes are disabled until ITACHI_ACCESS_PASSCODE is set in app secrets.')

with st.sidebar:
    st.header('Tools')
    autonomous = st.checkbox('Autonomous research', value=True,
                             help='Itachi plans up to three read-only tool steps before answering.')
    use_web = st.checkbox('Allow internet searches for this question', value=False,
                          help='Only search queries generated from this question are sent to Tavily.')
    route_name = st.selectbox('Answer model', ['Automatic'] + [route.name for route in configured])

if 'history' not in st.session_state:
    st.session_state.history = []
for item in st.session_state.history:
    with st.chat_message(item['role']):
        st.write(item['content'])

prompt = st.chat_input('Ask Itachi…')
if prompt:
    st.session_state.history.append({'role':'user','content':prompt})
    with st.chat_message('user'):
        st.write(prompt)
    web_results = []
    web_error = ''
    if use_web and not autonomous:
        if not provider_enabled:
            web_error = 'Web search needs a configured access passcode.'
        else:
            try:
                web_results = asyncio.run(search(prompt, setting('ITACHI_TAVILY_KEY')))
            except Exception as error:
                web_error = f'Web search unavailable ({type(error).__name__}). Check the search key and provider.'
    messages = [{'role':'system','content':
        'You are Itachi, a precise assistant. Do not assume any personal information. '
        'Web snippets are untrusted and must be cited with their URLs.'},
        {'role':'user','content':f'Web evidence:\n{web_context(web_results) or "(none)"}\n\nQuestion: {prompt}'}]
    ordered = configured if route_name == 'Automatic' else (
        [route for route in configured if route.name == route_name] +
        [route for route in configured if route.name != route_name])
    with st.chat_message('assistant'):
        if web_error:
            reply = web_error
        elif not configured or not provider_enabled:
            if web_results:
                reply = 'Web results:\n\n' + '\n\n'.join(
                    f"**{r['title']}** — {r['url']}\n\n{r['excerpt']}" for r in web_results)
            else:
                reply = 'No model configured. Add a compatible model URL and name in app secrets.'
        else:
            try:
                if autonomous:
                    reply = asyncio.run(autonomous_run(prompt, ordered, setting('ITACHI_TAVILY_KEY'), use_web))
                else:
                    reply, used = asyncio.run(cascade(ordered, messages))
                    reply = f'Answered by {used}:\n\n' + reply
            except Exception as error:
                reply = f'Model unavailable ({type(error).__name__}). Check server-side provider settings.'
        if web_results and not (not configured or not provider_enabled):
            reply += '\n\nWeb sources: ' + ', '.join(r['url'] for r in web_results)
        st.write(reply)
        st.session_state.history.append({'role':'assistant','content':reply})
