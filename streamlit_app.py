"""Hosted test console without personal knowledge ingestion."""
import asyncio
import hmac
import os
import time
import json
import streamlit as st

st.set_page_config(page_title='Itachi · Cognitive Node', page_icon='◉', layout='centered')

def browser_context(name: str, default: str = '') -> str:
    try:
        context = getattr(st, 'context', None)
        value = getattr(context, name, None) if context is not None else None
        if value is None:
            return default
        return str(value)
    except Exception:
        return default

def setting(name: str, default: str = '') -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except FileNotFoundError:
        return os.getenv(name, default)


def requires_fresh_web(prompt: str) -> bool:
    """Keep Streamlit boot-compatible with cached autonomy modules during hot reload."""
    text = prompt.lower() if isinstance(prompt, str) else ''
    return any(marker in text for marker in (
        'latest', 'current', 'today', 'tonight', 'this week', 'recent', 'news',
        'last ', 'most recent', 'winner', 'won ', 'champion', 'result', 'score',
        'weather', 'price', 'president', 'prime minister', 'ceo', 'version', 'release',
    ))

from backend.app.model_router import cascade
from backend.app.model_catalog import ModelRoute, parse
from backend.app.web_search import search, context as web_context
from backend.app.autonomy import run as autonomous_run
from backend.app.answer_guard import guaranteed_answer
from backend.app.model_selection import discover_hf, rank, record, HF_BASE
from backend.app.public_reference import reply as reference_reply
from backend.app.public_catalog import load as load_public_catalog
from backend.app.semantic_memory import SessionSemanticMemory, embed, format_context
from backend.app.public_knowledge import load as load_learned_knowledge, search as search_learned_knowledge, context as learned_context
from backend.app.jev import evaluate_prompt as jev_evaluate_prompt
from backend.app.google_oauth import oauth_config, issue_state, valid_state, authorization_url, exchange_code
from backend.app.client_context import client_context_text, local_clock_reply, normalize_timezone, weather_reply
from backend.app.itachi_face import FACE_COMPONENT_HTML, FACE_COMPONENT_CSS, FACE_COMPONENT_JS

face_component = st.components.v2.component(
    "itachi_reactive_face",
    html=FACE_COMPONENT_HTML,
    css=FACE_COMPONENT_CSS,
    js=FACE_COMPONENT_JS,
)

st.markdown('''<style>
html, body, [data-testid="stAppViewContainer"], .stApp {
  margin:0 !important;
  padding:0 !important;
  width:100vw !important;
  height:100vh !important;
  overflow:hidden !important;
  background:#010407 !important;
  color:#dce8f2;
}
[data-testid="stAppViewContainer"] > .main {
  width:100vw !important;
  height:100vh !important;
}
[data-testid="stAppViewContainer"] > .main .block-container {
  max-width:100vw !important;
  width:100vw !important;
  height:100vh !important;
  padding:0 !important;
  margin:0 !important;
  overflow:hidden !important;
}
[data-testid="stSidebar"] {display:none !important;}
[data-testid="collapsedControl"] {display:none !important;}
header[data-testid="stHeader"] {display:none !important;}
#MainMenu, footer {visibility:hidden !important;}

.st-key-itachi_transcript {
  position:fixed !important;
  left:50% !important;
  bottom:92px !important;
  transform:translateX(-50%) !important;
  width:min(920px,calc(100vw - 36px)) !important;
  max-height:30vh !important;
  overflow-y:auto !important;
  z-index:50 !important;
  padding:10px 12px !important;
  border:1px solid rgba(93,234,229,.10) !important;
  border-radius:18px !important;
  background:linear-gradient(180deg,rgba(3,10,15,.18),rgba(3,10,15,.74)) !important;
  backdrop-filter:blur(12px) !important;
  box-shadow:0 16px 50px rgba(0,0,0,.28),inset 0 0 24px rgba(57,211,210,.025) !important;
}
.st-key-itachi_transcript::-webkit-scrollbar {width:5px;}
.st-key-itachi_transcript::-webkit-scrollbar-thumb {
  background:rgba(91,231,225,.18);
  border-radius:99px;
}
[data-testid="stChatMessage"] {
  border:0 !important;
  border-bottom:1px solid rgba(105,230,226,.045) !important;
  background:transparent !important;
  padding:.45rem .25rem !important;
}
[data-testid="stChatMessage"]:last-child {border-bottom:0 !important;}
.itachi-response-label {
  color:#78eee8;
  font-size:.64rem;
  font-weight:750;
  letter-spacing:.22em;
  margin-bottom:.25rem;
  text-transform:uppercase;
}
[data-testid="stChatInput"] {
  position:fixed !important;
  left:50% !important;
  bottom:20px !important;
  transform:translateX(-50%) !important;
  width:min(920px,calc(100vw - 36px)) !important;
  z-index:80 !important;
}
[data-testid="stChatInput"] > div {
  border:1px solid rgba(91,233,228,.26) !important;
  background:rgba(5,16,23,.78) !important;
  backdrop-filter:blur(14px) !important;
  box-shadow:0 0 28px rgba(60,221,219,.05) !important;
}
[data-testid="stChatInput"] textarea {
  color:#e5f4f5 !important;
}
.stAlert, [data-testid="stTextInput"], .stButton {
  position:relative;
  z-index:90;
}
@media (max-width:700px) {
  .st-key-itachi_transcript {
    bottom:86px !important;
    max-height:33vh !important;
    width:calc(100vw - 22px) !important;
  }
  [data-testid="stChatInput"] {
    width:calc(100vw - 22px) !important;
    bottom:14px !important;
  }
}
</style>''', unsafe_allow_html=True)

face_slot = st.empty()
if 'face_render_nonce' not in st.session_state:
    st.session_state.face_render_nonce = 0
if 'face_mode' not in st.session_state:
    st.session_state.face_mode = 'idle'
if 'face_speak_text' not in st.session_state:
    st.session_state.face_speak_text = ''
if 'face_speech_id' not in st.session_state:
    st.session_state.face_speech_id = ''
if 'pending_prompt' not in st.session_state:
    st.session_state.pending_prompt = ''

def render_itachi_face(mode: str = 'idle', speak_text: str = '', speech_id: str = '',
                       voice_enabled: bool = True, mic_enabled: bool = False,
                       input_mode: bool = False):
    face_slot.empty()
    if not input_mode:
        st.session_state.face_render_nonce += 1
    key = 'itachi_face_input' if input_mode else f"itachi_face_{st.session_state.face_render_nonce}"
    with face_slot.container():
        return face_component(
            data={
                'mode': mode,
                'speak_text': speak_text,
                'speech_id': speech_id,
                'voice_enabled': voice_enabled,
                'mic_enabled': mic_enabled,
            },
            default={'transcript': {}, 'location': {}, 'mic_status': {}},
            key=key,
            on_transcript_change=lambda: None,
            on_location_change=lambda: None,
            on_mic_status_change=lambda: None,
        )

def itachi_response_label() -> None:
    st.markdown('<div class="itachi-response-label">ITACHI</div>', unsafe_allow_html=True)

face_state = render_itachi_face(
    st.session_state.face_mode,
    st.session_state.face_speak_text,
    st.session_state.face_speech_id,
    voice_enabled=True,
    mic_enabled=True,
    input_mode=True,
)

access_passcode = setting('ITACHI_ACCESS_PASSCODE')
if access_passcode and not st.session_state.get('authenticated', False):
    entered = st.text_input('Access passcode', type='password')
    if st.button('Unlock') and hmac.compare_digest(entered, access_passcode):
        st.session_state.authenticated = True
        st.rerun()
    st.stop()

google_oauth_json = setting('ITACHI_GOOGLE_OAUTH_JSON')
google_client_secret = setting('ITACHI_GOOGLE_CLIENT_SECRET')
google_oauth_ready = bool(google_oauth_json or google_client_secret)
google_refresh_token = ''

if access_passcode and st.session_state.get('authenticated', False) and google_oauth_ready:
    try:
        google_client_id, google_client_secret_value, google_redirect_uri = oauth_config(
            google_oauth_json,
            setting('ITACHI_GOOGLE_CLIENT_ID'),
            google_client_secret,
            setting('ITACHI_GOOGLE_REDIRECT_URI'),
        )
        google_code = str(st.query_params.get('code', '') or '')
        google_state = str(st.query_params.get('state', '') or '')
        google_error = str(st.query_params.get('error', '') or '')

        if google_error:
            st.error(f'Google Drive authorization failed: {google_error}')
        elif google_code:
            if not google_state or not valid_state(google_state, google_client_secret_value):
                st.error('Google Drive authorization state was invalid or expired.')
            else:
                try:
                    token_payload = asyncio.run(
                        exchange_code(
                            google_code,
                            google_client_id,
                            google_client_secret_value,
                            google_redirect_uri,
                        )
                    )
                    google_refresh_token = str(token_payload.get('refresh_token') or '')
                    if google_refresh_token:
                        st.session_state.google_refresh_token = google_refresh_token
                    else:
                        st.warning(
                            'Google authorized the account but did not return a refresh token. '
                            'Revoke the app grant if necessary and authorize again.'
                        )
                except Exception as error:
                    st.error(f'Google token exchange failed ({type(error).__name__}).')
            st.query_params.clear()
    except ValueError:
        pass

try:
    configured = parse(setting('ITACHI_MODEL_ROUTES_JSON'))
except ValueError:
    st.error('Invalid reasoning-engine configuration. Ask the app administrator to check the secret.')
    st.stop()
if not configured:
    for name, prefix in (('Reasoning', 'REASONING'), ('Fallback', 'FALLBACK')):
        url = setting(f'ITACHI_{prefix}_URL')
        model = setting(f'ITACHI_{prefix}_MODEL')
        if url and model:
            configured.append(ModelRoute(name, url, model, setting(f'ITACHI_{prefix}_KEY')))

nvidia_key = setting('ITACHI_NVIDIA_API_KEY')
nvidia_base_url = setting('ITACHI_NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1').rstrip('/')
nvidia_chat_model = setting('ITACHI_NVIDIA_CHAT_MODEL', 'nvidia/nemotron-3-ultra-550b-a55b')
if nvidia_key and len(configured) < 5 and not any(r.name == 'NVIDIA Nemotron Ultra' for r in configured):
    configured.append(ModelRoute('NVIDIA Nemotron Ultra', nvidia_base_url,
                                 nvidia_chat_model, nvidia_key))

groq_key = setting('ITACHI_GROQ_API_KEY')
if groq_key and len(configured) < 5 and not any(r.name == 'Groq Qwen' for r in configured):
    configured.append(ModelRoute('Groq Qwen', 'https://api.groq.com/openai/v1',
                                 'qwen/qwen3.8-27b', groq_key))

gemini_key = setting('ITACHI_GEMINI_API_KEY')
if gemini_key and len(configured) < 5 and not any(r.name == 'Gemini Flash' for r in configured):
    configured.append(ModelRoute('Gemini Flash', 'https://generativelanguage.googleapis.com/v1beta/openai',
                                 'gemini-3.8-flash', gemini_key))

cerebras_key = setting('ITACHI_CEREBRAS_API_KEY')
if cerebras_key and len(configured) < 5 and not any(r.name == 'Cerebras GPT OSS' for r in configured):
    configured.append(ModelRoute('Cerebras GPT OSS', 'https://api.cerebras.ai/v1',
                                 'gpt-oss-120b', cerebras_key))

openrouter_key = setting('ITACHI_OPENROUTER_API_KEY')
if openrouter_key and len(configured) < 5 and not any(r.name == 'OpenRouter Free' for r in configured):
    configured.append(ModelRoute('OpenRouter Free', 'https://openrouter.ai/api/v1',
                                 'openrouter/free', openrouter_key))

typesafe_key = setting('TYPESAFE_API_KEY', setting('ITACHI_JEV_TOKEN'))

rapidapi_key = setting('ITACHI_RAPIDAPI_KEY')

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
    st.warning('Itachi reasoning is locked until ITACHI_ACCESS_PASSCODE is set in app secrets.')

if 'history' not in st.session_state:
    st.session_state.history = []
if 'route_feedback' not in st.session_state:
    st.session_state.route_feedback = {}
if 'semantic_memory' not in st.session_state:
    st.session_state.semantic_memory = SessionSemanticMemory()
if 'memory_error' not in st.session_state:
    st.session_state.memory_error = ''
if 'jev_error' not in st.session_state:
    st.session_state.jev_error = ''

memory_enabled = bool(nvidia_key)
client_timezone = normalize_timezone(browser_context('timezone', 'UTC'))
client_locale = browser_context('locale', '')
precise_location = False
client_latitude = None
client_longitude = None
client_accuracy = None
learned_knowledge = load_learned_knowledge()

with st.sidebar:
    snapshot = load_public_catalog()
    st.caption(f"Public repository snapshot: {len(snapshot.get('repositories', []))} sources")
    st.caption(f"Learned public knowledge: {len(learned_knowledge)} records")
    st.download_button('Download public catalog', data=json.dumps(snapshot, indent=2),
                       file_name='itachi-public-catalog.json', mime='application/json')
    st.caption(f"Cognitive engine: {'online' if configured and provider_enabled else 'offline'}")
    st.caption(f"Semantic memory: {'ready' if memory_enabled else 'off'}")
    st.caption(f"Decision layer: {'ready' if typesafe_key else 'off'}")
    st.caption(f"RapidAPI specialists: {'ready' if rapidapi_key else 'off'}")
    st.caption(f"Google OAuth bootstrap: {'ready' if google_oauth_ready else 'off'}")
    st.caption(f"Browser timezone: {client_timezone}")
    location_value = getattr(face_state, 'location', None)
    if hasattr(location_value, 'get'):
        precise_location = location_value.get('status') == 'granted'
        client_latitude = location_value.get('latitude') if precise_location else None
        client_longitude = location_value.get('longitude') if precise_location else None
        client_accuracy = location_value.get('accuracy') if precise_location else None
    if precise_location:
        st.caption('Precise location: enabled for this browser session only')
    else:
        st.caption('Precise location: off — timezone fallback active')
    if st.session_state.memory_error:
        st.caption(f"Memory status: {st.session_state.memory_error}")
    if st.session_state.jev_error:
        st.caption(f"Decision status: {st.session_state.jev_error}")
    if hf_token and st.session_state.get('hf_discovery_error'):
        st.caption('Optional model discovery is unavailable; configured routes may still work.')
    st.header('Tools')
    autonomous = st.checkbox('Autonomous reasoning & research', value=True,
                             help='Itachi chooses bounded read-only tools, verifies evidence, and can critique deep answers.')
    answer_depth = st.selectbox(
        'Response depth',
        ['Auto', 'Quick', 'Deep'],
        index=0,
        help='Auto adapts to the question. Quick minimizes model/tool calls. Deep adds broader research and a critique/revision pass.'
    )
    use_web = st.checkbox('Allow internet research', value=True,
                          help='Itachi decides when fresh public information is useful. Personal data and secrets are excluded from search queries.')
    voice_enabled = st.checkbox(
        'Voice responses',
        value=True,
        help='Speaks Itachi replies using the best calm English voice available in this browser.'
    )
    use_memory = st.checkbox(
        'Use session semantic memory',
        value=memory_enabled,
        disabled=not memory_enabled,
        help='Keeps semantic context for this Streamlit session only.'
    )
    route_name = 'Automatic'

    if access_passcode and st.session_state.get('authenticated', False):
        with st.expander('Google Drive admin'):
            if not google_oauth_ready:
                st.info(
                    'Add ITACHI_GOOGLE_CLIENT_SECRET or ITACHI_GOOGLE_OAUTH_JSON '
                    'to Streamlit Secrets to enable Google Drive authorization.'
                )
            else:
                try:
                    google_client_id, google_client_secret_value, google_redirect_uri = oauth_config(
                        google_oauth_json,
                        setting('ITACHI_GOOGLE_CLIENT_ID'),
                        google_client_secret,
                        setting('ITACHI_GOOGLE_REDIRECT_URI'),
                    )
                    oauth_state = issue_state(google_client_secret_value)
                    oauth_url = authorization_url(
                        google_client_id,
                        google_redirect_uri,
                        oauth_state,
                        'project.itachi.storage@gmail.com',
                    )
                    st.link_button('Connect Itachi Google Drive', oauth_url)
                    st.caption(
                        'Uses Google drive.file access and requests offline authorization '
                        'so the scheduled backup can refresh access without you being present.'
                    )
                    stored_refresh = str(st.session_state.get('google_refresh_token') or '')
                    if stored_refresh:
                        st.success('Google Drive authorization completed.')
                        st.text_area(
                            'ITACHI_GOOGLE_REFRESH_TOKEN — copy once to GitHub Actions secrets',
                            value=stored_refresh,
                            height=100,
                        )
                        st.caption(
                            'After saving it in GitHub Actions secrets, clear this browser session '
                            'or reload the app. The token is not written to GitHub by Itachi.'
                        )
                except ValueError as error:
                    st.info(str(error))

client_context = client_context_text(
    client_timezone,
    client_locale,
    precise_location=precise_location,
)

with st.container(key='itachi_transcript'):
    for index, item in enumerate(st.session_state.history[-8:]):
        with st.chat_message(item['role']):
            if item['role'] == 'assistant':
                itachi_response_label()
            st.write(item['content'])

typed_prompt = st.chat_input('Ask Itachi…')
voice_prompt = ''
voice_event = getattr(face_state, 'transcript', None)
if hasattr(voice_event, 'get'):
    voice_id = str(voice_event.get('id') or '')
    voice_text = str(voice_event.get('text') or '').strip()
    if voice_id and voice_text and voice_id != st.session_state.get('last_voice_transcript_id', ''):
        st.session_state.last_voice_transcript_id = voice_id
        voice_prompt = voice_text

submitted_prompt = (typed_prompt or voice_prompt or '').strip()
if submitted_prompt and not st.session_state.pending_prompt:
    st.session_state.history.append({'role':'user', 'content':submitted_prompt})
    st.session_state.pending_prompt = submitted_prompt
    st.session_state.face_mode = 'thinking'
    st.session_state.face_speak_text = ''
    st.session_state.face_speech_id = ''
    st.rerun()

prompt = str(st.session_state.pending_prompt or '').strip()
if prompt:
    utility_reply = local_clock_reply(
        prompt,
        client_timezone,
        client_locale,
        client_latitude,
        client_longitude,
        client_accuracy,
    )
    if utility_reply is None:
        try:
            utility_reply = asyncio.run(
                weather_reply(
                    prompt,
                    client_timezone,
                    client_locale,
                    client_latitude,
                    client_longitude,
                )
            )
        except Exception as error:
            if any(word in prompt.lower() for word in ('weather', 'forecast', 'temperature')):
                utility_reply = (
                    f'Local weather lookup is temporarily unavailable ({type(error).__name__}). '
                    'Time and date context are still available from your browser timezone.'
                )

    if utility_reply is not None:
        reply = str(utility_reply).strip()
        st.session_state.history.append({
            'role':'assistant',
            'content':reply,
            'route':'',
        })
        st.session_state.pending_prompt = ''
        st.session_state.face_mode = 'speaking'
        st.session_state.face_speak_text = reply
        st.session_state.face_speech_id = str(time.time_ns())
        st.rerun()

    jev_task = ''
    jev_web = bool(use_web)
    if typesafe_key:
        try:
            jev_decision = asyncio.run(jev_evaluate_prompt(prompt, typesafe_key))
            jev_task = jev_decision.task
            st.session_state.jev_error = ''
        except Exception as error:
            st.session_state.jev_error = f'unavailable ({type(error).__name__}); using built-in routing'

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

    learned_results = search_learned_knowledge(prompt, learned_knowledge, limit=5)
    learned_public_context = learned_context(learned_results)

    ordered = rank(
        configured,
        prompt,
        st.session_state.route_feedback,
        task_override=jev_task,
    )

    context_parts = []
    if recalled_context != '(none)':
        context_parts.append(f"Relevant session memory:\n{recalled_context}")
    if learned_public_context != '(none)':
        context_parts.append(f"Learned public knowledge:\n{learned_public_context}")
    context_parts.append(f"Client context:\n{client_context}")
    autonomous_context = "\n\n".join(context_parts)

    used = ''
    try:
        if configured and provider_enabled:
            reply, used = asyncio.run(
                guaranteed_answer(
                    prompt,
                    ordered,
                    setting('ITACHI_TAVILY_KEY'),
                    allow_web=bool(jev_web or requires_fresh_web(prompt)),
                    depth=answer_depth.lower(),
                    extra_context=autonomous_context,
                    rapidapi_key=rapidapi_key,
                )
            )
        else:
            reply = asyncio.run(reference_reply(prompt, True))
    except Exception as error:
        try:
            reply = asyncio.run(reference_reply(prompt, True))
        except Exception:
            reply = (
                f'I could not complete the answer pipeline just now ({type(error).__name__}). '
                'Please ask me again; I am still online.'
            )

    reply = str(reply or '').strip()
    if not reply:
        reply = 'I could not produce a complete answer just now. Please ask me again; I am still online.'

    if used:
        for route in ordered:
            if route.name == used:
                record(st.session_state.route_feedback, used, True)
                break

    st.session_state.history.append({
        'role':'assistant',
        'content':reply,
        'route':used,
    })

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

    st.session_state.pending_prompt = ''
    st.session_state.face_mode = 'speaking'
    st.session_state.face_speak_text = reply
    st.session_state.face_speech_id = str(time.time_ns())
    st.rerun()
