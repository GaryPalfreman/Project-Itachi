"""Verify a local NVIDIA embedding checkpoint and fetch its matching small files."""
import argparse
import json
from pathlib import Path

from scripts.inspect_local_weights import inspect, NEMOTRON_EMBED_SHA256

MODEL_ID = 'nvidia/Nemotron-3-Embed-1B-BF16'
REVISION = '18abd04873998492fdbb52aa48eb4bdde53c3593'


def prepare(weights: Path, destination: Path) -> Path:
    weights = weights.expanduser().resolve(strict=True)
    destination = destination.expanduser().resolve()
    result = inspect(weights, hash_weights=True)
    if result['sha256'] != NEMOTRON_EMBED_SHA256:
        raise ValueError('Checkpoint SHA-256 does not match the pinned NVIDIA embedding model')
    if destination == weights.parent or destination.is_relative_to(weights.parent):
        raise ValueError('Choose a separate destination directory for companion files')
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / 'model.safetensors'
    if target.exists() or target.is_symlink():
        if not target.is_symlink() or target.resolve() != weights:
            raise ValueError('Destination already contains different model weights')
    else:
        target.symlink_to(weights)
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise RuntimeError('Install huggingface_hub first: python3 -m pip install huggingface_hub') from error
    snapshot_download(repo_id=MODEL_ID, revision=REVISION, local_dir=str(destination),
                      ignore_patterns=['*.safetensors', '*.bin', '*.pt', '*.pth'])
    for filename in ('config.json', 'tokenizer_config.json', 'modules.json'):
        if not (destination / filename).is_file():
            raise RuntimeError(f'Missing expected NVIDIA companion file: {filename}')
    (destination / 'itachi-model-origin.json').write_text(json.dumps({
        'repo': MODEL_ID, 'revision': REVISION, 'sha256': NEMOTRON_EMBED_SHA256,
        'purpose': 'embeddings only; not chat completions',
    }, indent=2) + '\n')
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weights', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        print('Prepared local embeddings in:', prepare(args.weights, args.destination))
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
