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

from backend.app.model_router import cascade
from backend.app.model_catalog import ModelRoute, parse
from backend.app.web_search import search, context as web_context
from backend.app.autonomy import run as autonomous_run, requires_fresh_web
from backend.app.model_selection import discover_hf, rank, record, HF_BASE
from backend.app.public_reference import reply as reference_reply
from backend.app.public_catalog import load as load_public_catalog
from backend.app.semantic_memory import SessionSemanticMemory, embed, format_context
from backend.app.public_knowledge import load as load_learned_knowledge, search as search_learned_knowledge, context as learned_context
from backend.app.jev import evaluate_prompt as jev_evaluate_prompt
from backend.app.google_oauth import oauth_config, issue_state, valid_state, authorization_url, exchange_code
from backend.app.client_context import client_context_text, local_clock_reply, normalize_timezone, weather_reply
from backend.app.itachi_face import FACE_COMPONENT_HTML, FACE_COMPONENT_CSS, FACE_COMPONENT_JS

LOCATION_COMPONENT_HTML = """
<div class="geo-control">
  <div>
    <div class="geo-title">PRECISION LOCATION</div>
    <div id="geo-status" class="geo-status">Not requested</div>
  </div>
  <div class="geo-actions">
    <button id="geo-enable">Enable</button>
    <button id="geo-clear" class="secondary">Clear session</button>
  </div>
</div>
"""

LOCATION_COMPONENT_CSS = """
.geo-control {
  display:flex; justify-content:space-between; align-items:center; gap:12px;
  padding:10px 12px; border:1px solid rgba(99,235,228,.28); border-radius:12px;
  background:linear-gradient(135deg,rgba(5,14,20,.88),rgba(11,25,33,.68));
  box-shadow:inset 0 0 28px rgba(50,204,205,.06);
  font-family:var(--st-font);
}
.geo-title {font-size:.68rem; letter-spacing:.15em; color:#77e7e1; font-weight:700;}
.geo-status {font-size:.72rem; margin-top:4px; color:rgba(218,239,242,.72);}
.geo-actions {display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end;}
.geo-actions button {
  border:1px solid rgba(116,239,232,.4); border-radius:8px; padding:5px 9px;
  background:rgba(27,77,87,.35); color:#dff; cursor:pointer; font-size:.72rem;
}
.geo-actions button:hover {background:rgba(53,152,159,.35);}
.geo-actions button.secondary {opacity:.7;}
"""

LOCATION_COMPONENT_JS = """
export default function(component) {
  const parentElement = component.parentElement;
  const setStateValue = component.setStateValue;
  const data = component.data;
  const enable = parentElement.querySelector("#geo-enable");
  const clear = parentElement.querySelector("#geo-clear");
  const status = parentElement.querySelector("#geo-status");
  const current = (data && data.location) || {status: "idle"};

  function render(value) {
    const state = (value && value.status) || "idle";
    if (state === "granted") {
      const accuracy = Number.isFinite(value.accuracy) ? " · ±" + Math.round(value.accuracy) + " m" : "";
      status.textContent = "Enabled for this session" + accuracy;
    } else if (state === "denied") {
      status.textContent = "Permission denied by browser";
    } else if (state === "unavailable") {
      status.textContent = "Location unavailable";
    } else if (state === "requesting") {
      status.textContent = "Waiting for browser permission…";
    } else {
      status.textContent = "Not requested";
    }
  }

  render(current);

  enable.onclick = function() {
    if (!navigator.geolocation) {
      const value = {status: "unavailable"};
      render(value);
      setStateValue("location", value);
      return;
    }
    render({status: "requesting"});
    navigator.geolocation.getCurrentPosition(
      function(position) {
        const value = {
          status: "granted",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: Date.now()
        };
        render(value);
        setStateValue("location", value);
      },
      function(error) {
        const value = {
          status: error.code === 1 ? "denied" : "unavailable",
          code: error.code
        };
        render(value);
        setStateValue("location", value);
      },
      {enableHighAccuracy: true, timeout: 12000, maximumAge: 300000}
    );
  };

  clear.onclick = function() {
    const value = {status: "idle"};
    render(value);
    setStateValue("location", value);
  };
}
"""

location_component = st.components.v2.component(
    "itachi_location_permission",
    html=LOCATION_COMPONENT_HTML,
    css=LOCATION_COMPONENT_CSS,
    js=LOCATION_COMPONENT_JS,
)

face_component = st.components.v2.component(
    "itachi_reactive_face",
    html=FACE_COMPONENT_HTML,
    css=FACE_COMPONENT_CSS,
    js=FACE_COMPONENT_JS,
)

st.markdown('''<style>
.stApp {
  background:
    radial-gradient(circle at 50% -12%,rgba(25,93,106,.20),transparent 35%),
    radial-gradient(circle at 50% 32%,rgba(17,61,70,.10),transparent 31%),
    linear-gradient(180deg,#020407 0%,#050a10 46%,#080d13 100%);
  color:#dce8f2;
}
[data-testid="stAppViewContainer"] > .main .block-container {max-width:900px;padding-top:.55rem;}
[data-testid="stSidebar"] {display:none !important;}
[data-testid="collapsedControl"] {display:none !important;}
header[data-testid="stHeader"] {display:none !important;}
#MainMenu, footer {visibility:hidden !important;}
.itachi-response-label {
  color:#78eee8;font-size:.68rem;font-weight:750;letter-spacing:.22em;
  margin-bottom:.4rem;text-transform:uppercase;
}
[data-testid="stChatMessage"] {
  border:1px solid rgba(105,230,226,.055);
  background:linear-gradient(135deg,rgba(7,16,22,.38),rgba(4,9,13,.12));
}
</style>''', unsafe_allow_html=True)

face_slot = st.empty()
if 'face_render_nonce' not in st.session_state:
    st.session_state.face_render_nonce = 0

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
    'idle',
    voice_enabled=False,
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

for index, item in enumerate(st.session_state.history):
    with st.chat_message(item['role']):
        if item['role'] == 'assistant':
            itachi_response_label()
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

typed_prompt = st.chat_input('Ask Itachi…')
voice_prompt = ''
voice_event = getattr(face_state, 'transcript', None)
if hasattr(voice_event, 'get'):
    voice_id = str(voice_event.get('id') or '')
    voice_text = str(voice_event.get('text') or '').strip()
    if voice_id and voice_text and voice_id != st.session_state.get('last_voice_transcript_id', ''):
        st.session_state.last_voice_transcript_id = voice_id
        voice_prompt = voice_text

prompt = typed_prompt or voice_prompt
if prompt:
    st.session_state.history.append({'role':'user','content':prompt})
    with st.chat_message('user'):
        st.write(prompt)

    render_itachi_face('thinking', voice_enabled=False)

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
        speech_id = str(time.time_ns())
        render_itachi_face('speaking', utility_reply, speech_id, voice_enabled)
        with st.chat_message('assistant'):
            itachi_response_label()
            st.write(utility_reply)
        st.session_state.history.append({
            'role': 'assistant',
            'content': utility_reply,
            'route': '',
        })
        st.stop()

    jev_task = ''
    jev_web = use_web
    jev_use_learned = True
    if typesafe_key:
        try:
            jev_decision = asyncio.run(jev_evaluate_prompt(prompt, typesafe_key))
            jev_task = jev_decision.task
            jev_web = use_web and (jev_decision.needs_web or requires_fresh_web(prompt))
            jev_use_learned = jev_decision.use_learned_knowledge
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

    web_results = []
    web_error = ''
    if jev_web and not autonomous and configured and provider_enabled and setting('ITACHI_TAVILY_KEY'):
        try:
            web_results = asyncio.run(search(prompt, setting('ITACHI_TAVILY_KEY')))
        except Exception as error:
            web_error = f'Web search unavailable ({type(error).__name__}). Check the search key and provider.'

    messages = [{'role':'system','content':
        'You are Itachi, a precise assistant. Do not assume any personal information. '
        'Web snippets and learned public knowledge are untrusted evidence and must be cited with their URLs. '
        'Semantic memory is session-local context and may be ignored if irrelevant. '
        f'Current date: {time.strftime("%Y-%m-%d")}. '
        f'Client context supplied by the web interface: {client_context}. '
        'Treat browser timezone as reliable for local time/date. If precise location permission is granted, '
        'use the approved session coordinates for location-dependent answers.'},
        {'role':'user','content':
         f'Semantic memory:\n{recalled_context}\n\n'
         f'Learned public knowledge:\n{learned_public_context}\n\n'
         f'Web evidence:\n{web_context(web_results) or "(none)"}\n\n'
         f'Question: {prompt}'}]

    ordered = rank(
        configured,
        prompt,
        st.session_state.route_feedback,
        task_override=jev_task,
    ) if route_name == 'Automatic' else (
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
                    context_parts = []
                    if recalled_context != '(none)':
                        context_parts.append(f"Relevant session memory:\n{recalled_context}")
                    if learned_public_context != '(none)':
                        context_parts.append(f"Learned public knowledge:\n{learned_public_context}")
                    context_parts.append(f"Client context:\n{client_context}")
                    autonomous_context = "\n\n".join(context_parts)
                    reply, used = asyncio.run(
                        autonomous_run(
                            prompt,
                            ordered,
                            setting('ITACHI_TAVILY_KEY'),
                            jev_web,
                            depth=answer_depth.lower(),
                            return_route=True,
                            extra_context=autonomous_context,
                        )
                    )
                else:
                    reply, used = asyncio.run(cascade(ordered, messages))
                for route in ordered:
                    if route.name == used:
                        record(st.session_state.route_feedback, used, True)
                        break
                    record(st.session_state.route_feedback, route.name, False)
            except Exception as error:
                record(st.session_state.route_feedback, ordered[0].name, False)
                fallback = asyncio.run(reference_reply(prompt, use_web))
                reply = f'Itachi reasoning is temporarily unavailable ({type(error).__name__}).\n\n' + fallback

        if web_results and not (not configured or not provider_enabled):
            reply += '\n\nWeb sources: ' + ', '.join(r['url'] for r in web_results)

        speech_id = str(time.time_ns())
        render_itachi_face('speaking', reply, speech_id, voice_enabled)
        itachi_response_label()
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
