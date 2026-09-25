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
    vault: Path = Path(os.getenv('ITACHI_VAULT', './examples/vault')).expanduser().resolve()
    reasoning_url: str = os.getenv('ITACHI_REASONING_URL', 'http://127.0.0.1:11434/v1')
    reasoning_model: str = os.getenv('ITACHI_REASONING_MODEL', 'nemotron-mini:4b')
    reasoning_key: str = os.getenv('ITACHI_REASONING_KEY', '')
    fallback_url: str = os.getenv('ITACHI_FALLBACK_URL', '')
    fallback_model: str = os.getenv('ITACHI_FALLBACK_MODEL', '')
    fallback_key: str = os.getenv('ITACHI_FALLBACK_KEY', '')
    coding_url: str = os.getenv('ITACHI_CODING_URL', '')
    coding_model: str = os.getenv('ITACHI_CODING_MODEL', '')
    coding_key: str = os.getenv('ITACHI_CODING_KEY', '')
    openclaw_url: str = os.getenv('ITACHI_OPENCLAW_URL', '')
    openclaw_token: str = os.getenv('ITACHI_OPENCLAW_TOKEN', '')
    jev_url: str = os.getenv('ITACHI_JEV_URL', '')
    jev_token: str = os.getenv('ITACHI_JEV_TOKEN', '')
    piper_voice: str = os.getenv('ITACHI_PIPER_VOICE', '')
    whisper_model: str = os.getenv('ITACHI_WHISPER_MODEL', 'base.en')

settings = Config()
