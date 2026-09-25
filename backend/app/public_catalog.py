"""Load only the checked-in, bounded public metadata snapshot."""
import json
from pathlib import Path

FILE = Path(__file__).resolve().parents[2] / 'data/public_catalog.json'


def load() -> dict:
    try:
        if FILE.stat().st_size > 100_000:
            raise ValueError('Public catalog exceeds size limit')
        value = json.loads(FILE.read_text(encoding='utf-8'))
        if not isinstance(value, dict) or not isinstance(value.get('repositories'), list):
            raise ValueError('Invalid public catalog')
        return value
    except (OSError, ValueError):
        return {'generated_at':None, 'repositories':[]}
