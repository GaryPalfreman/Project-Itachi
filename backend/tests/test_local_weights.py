import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.inspect_local_weights import inspect


class LocalWeightsTests(unittest.TestCase):
    def test_inspect_header_without_loading_large_weight_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = json.dumps({'layer.weight': {'dtype': 'F32', 'shape': [1],
                                                   'data_offsets': [0, 4]}}).encode()
            (root / 'model.safetensors').write_bytes(struct.pack('<Q', len(header)) + header + b'\0' * 4)
            (root / 'config.json').write_text('{"model_type":"nemotron_h","architectures":["NemotronHForCausalLM"]}')
            (root / 'tokenizer_config.json').write_text('{}')
            result = inspect(root / 'model.safetensors')
            self.assertEqual(result['model_type'], 'nemotron_h')
            self.assertEqual(result['tensor_count'], 1)
            self.assertTrue(result['basic_files_present'])
            self.assertNotIn('data_offsets', result)

    def test_missing_and_malformed_weights_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.safetensors'
            with self.assertRaises(ValueError):
                inspect(path)
            path.write_bytes(struct.pack('<Q', 30) + b'{}')
            with self.assertRaises(ValueError):
                inspect(path)


if __name__ == '__main__':
    unittest.main()
