"""Read-only inventory on the Mac; does not print OpenClaw tokens or alter settings."""
import json
import os
from pathlib import Path
from urllib.request import urlopen


def main():
    if os.getenv('ITACHI_ENABLE_KNOWLEDGE', '').lower() == 'true':
        vault = Path(os.path.expanduser(os.getenv('ITACHI_VAULT', 'examples/vault')))
        print('Configured knowledge directory:', vault, '| exists:', vault.is_dir())
    else:
        print('Knowledge access disabled; no files scanned.')
    try:
        with urlopen('http://127.0.0.1:11434/api/tags', timeout=3) as response:
            models = json.load(response).get('models', [])
        print('Ollama models:')
        for model in models:
            print(' -', model.get('name', '(unknown)'))
    except (OSError, ValueError) as error:
        print('Ollama unavailable:', type(error).__name__)
    print('OpenClaw: configure ITACHI_OPENCLAW_URL only after its HTTP chat endpoint is enabled.')


if __name__ == '__main__':
    main()
