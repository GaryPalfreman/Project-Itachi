"""Inspect a local safetensors header and adjacent model files without loading weights."""
import argparse
import json
import struct
from pathlib import Path

MAX_HEADER = 16 * 1024 * 1024
REQUIRED_COMPANIONS = ('config.json', 'tokenizer.json', 'tokenizer_config.json',
                       'model.safetensors.index.json', 'adapter_config.json')


def inspect(path: Path) -> dict:
    path = path.expanduser().resolve()
    if not path.is_file() or path.suffix != '.safetensors':
        raise ValueError('Pass an existing .safetensors file')
    with path.open('rb') as handle:
        length_bytes = handle.read(8)
        if len(length_bytes) != 8:
            raise ValueError('Truncated safetensors file')
        length = struct.unpack('<Q', length_bytes)[0]
        if not 2 <= length <= MAX_HEADER or path.stat().st_size < 8 + length:
            raise ValueError('Invalid or oversized safetensors header')
        try:
            header = json.loads(handle.read(length))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError('Invalid safetensors JSON header') from error
    if not isinstance(header, dict):
        raise ValueError('Invalid safetensors header structure')
    keys = [key for key in header if key != '__metadata__']
    if not keys or any(not isinstance(header[key], dict) for key in keys):
        raise ValueError('No tensor entries found')
    config_file = path.parent / 'config.json'
    adapter_file = path.parent / 'adapter_config.json'
    config = {}
    if config_file.is_file():
        try:
            config = json.loads(config_file.read_text(encoding='utf-8'))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError('Invalid config.json') from error
        if not isinstance(config, dict):
            raise ValueError('Invalid config.json structure')
    companions = {name: (path.parent / name).is_file() for name in REQUIRED_COMPANIONS}
    return {
        'weights_bytes': path.stat().st_size,
        'tensor_count': len(keys),
        'model_type': str(config.get('model_type', 'unknown'))[:80],
        'architectures': [str(x)[:100] for x in config.get('architectures', [])[:5]]
            if isinstance(config.get('architectures', []), list) else [],
        'companion_files': companions,
        'adapter': adapter_file.is_file(),
        'basic_files_present': bool(config_file.is_file() and
                                    (companions['tokenizer.json'] or companions['tokenizer_config.json']) and
                                    not adapter_file.is_file()),
        'note': 'Header and files only; identity, completeness, license and runtime support must still be verified.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path, help='The local model.safetensors path')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.file), indent=2))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
