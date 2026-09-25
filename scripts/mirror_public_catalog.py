"""Mirror the checked-in public snapshot to optional authorized HTTPS object endpoints."""
import asyncio
import os
from pathlib import Path
from backend.app.mirrors import parse, upload

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    mirrors = parse(os.getenv('ITACHI_MIRRORS_JSON', ''))
    if mirrors:
        payload = (ROOT / 'data/public_catalog.json').read_bytes()
        completed = asyncio.run(upload(payload, mirrors))
        print('Updated optional mirrors:', ', '.join(completed))
    else:
        print('No external mirrors configured')
