"""Inspect a local safetensors header and adjacent model files without loading weights."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

MAX_HEADER = 16 * 1024 * 1024
NEMOTRON_EMBED_SHA256 = 'f959c3b04e66b42de280bfb97c140cb7e0bfe25e3ecb0b4464c68a8436b2d04f'
REQUIRED_COMPANIONS = ('config.json', 'tokenizer.json', 'tokenizer_config.json',
                       'model.safetensors.index.json', 'adapter_config.json')


def inspect(path: Path, hash_weights: bool = False) -> dict:
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
    result = {
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
    if hash_weights:
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b''):
                digest.update(chunk)
        result['sha256'] = digest.hexdigest()
        if result['sha256'] == NEMOTRON_EMBED_SHA256:
            result['verified_match'] = 'nvidia/Nemotron-3-Embed-1B-BF16 (embedding model, not chat)'
        else:
            result['verified_match'] = None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path, help='The local model.safetensors path')
    parser.add_argument('--sha256', action='store_true', help='Hash all weights to verify exact model identity')
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.file, hash_weights=args.sha256), indent=2))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
