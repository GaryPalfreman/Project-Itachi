import json
import hashlib
import struct
import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.inspect_local_weights import inspect
from scripts import prepare_local_embed


class LocalWeightsTests(unittest.TestCase):
    def test_inspect_header_without_loading_large_weight_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = json.dumps({'layer.weight': {'dtype': 'F32', 'shape': [1],
                                                   'data_offsets': [0, 4]}}).encode()
            (root / 'model.safetensors').write_bytes(struct.pack('<Q', len(header)) + header + b'\0' * 4)
            (root / 'config.json').write_text('{"model_type":"nemotron_h","architectures":["NemotronHForCausalLM"]}')
            (root / 'tokenizer_config.json').write_text('{}')
            result = inspect(root / 'model.safetensors', hash_weights=True)
            self.assertEqual(result['model_type'], 'nemotron_h')
            self.assertEqual(result['tensor_count'], 1)
            self.assertTrue(result['basic_files_present'])
            self.assertNotIn('data_offsets', result)
            self.assertEqual(result['sha256'], hashlib.sha256((root / 'model.safetensors').read_bytes()).hexdigest())
            self.assertIsNone(result['verified_match'])

    def test_missing_and_malformed_weights_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.safetensors'
            with self.assertRaises(ValueError):
                inspect(path)
            path.write_bytes(struct.pack('<Q', 30) + b'{}')
            with self.assertRaises(ValueError):
                inspect(path)

    def test_companion_download_requires_exact_checkpoint_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'downloads').mkdir()
            weights = Path(directory) / 'downloads' / 'model.safetensors'
            header = json.dumps({'weight': {'dtype': 'F32', 'shape': [1],
                                            'data_offsets': [0, 4]}}).encode()
            weights.write_bytes(struct.pack('<Q', len(header)) + header + b'\0' * 4)
            output = Path(directory) / 'prepared'
            called = []
            def fake_download(**arguments):
                called.append(arguments)
                for name in ('config.json', 'tokenizer_config.json', 'modules.json'):
                    (output / name).write_text('{}')
            with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=fake_download)}):
                with self.assertRaises(ValueError):
                    prepare_local_embed.prepare(weights, output)
                self.assertFalse(called)
                with patch.object(prepare_local_embed, 'NEMOTRON_EMBED_SHA256',
                                  hashlib.sha256(weights.read_bytes()).hexdigest()):
                    prepared = prepare_local_embed.prepare(weights, output)
            self.assertEqual(prepared, output)
            self.assertEqual((output / 'model.safetensors').resolve(), weights.resolve())
            self.assertEqual(called[0]['repo_id'], 'nvidia/Nemotron-3-Embed-1B-BF16')


if __name__ == '__main__':
    unittest.main()
