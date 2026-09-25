import os
from dataclasses import dataclass
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')

@dataclass(frozen=True)
class Config:
    vault: Path = Path(os.getenv('ITACHI_VAULT', str(Path(__file__).resolve().parents[2] / 'examples' / 'vault'))).expanduser().resolve()
    knowledge_enabled: bool = os.getenv('ITACHI_ENABLE_KNOWLEDGE', '').lower() == 'true'
    reasoning_url: str = os.getenv('ITACHI_REASONING_URL', 'http://127.0.0.1:11434/v1')
    reasoning_model: str = os.getenv('ITACHI_REASONING_MODEL', 'llama3.2:3b')
    reasoning_key: str = os.getenv('ITACHI_REASONING_KEY', '')
    fallback_url: str = os.getenv('ITACHI_FALLBACK_URL', '')
    fallback_model: str = os.getenv('ITACHI_FALLBACK_MODEL', '')
    fallback_key: str = os.getenv('ITACHI_FALLBACK_KEY', '')
    coding_url: str = os.getenv('ITACHI_CODING_URL', '')
    coding_model: str = os.getenv('ITACHI_CODING_MODEL', '')
    coding_key: str = os.getenv('ITACHI_CODING_KEY', '')
    openclaw_url: str = os.getenv('ITACHI_OPENCLAW_URL', '')
    openclaw_token: str = os.getenv('ITACHI_OPENCLAW_TOKEN', '')
    jev_url: str = os.getenv('ITACHI_JEV_URL', 'https://api.typesafe.ai/v1/systemone')
    jev_token: str = os.getenv('TYPESAFE_API_KEY', os.getenv('ITACHI_JEV_TOKEN', ''))
    piper_voice: str = os.getenv('ITACHI_PIPER_VOICE', '')
    whisper_model: str = os.getenv('ITACHI_WHISPER_MODEL', 'base.en')
    web_key: str = os.getenv('ITACHI_TAVILY_KEY', '')
    model_routes_json: str = os.getenv('ITACHI_MODEL_ROUTES_JSON', '')

settings = Config()
