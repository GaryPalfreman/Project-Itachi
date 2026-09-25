import io
import unittest
import zipfile
from app.vault_import import load_markdown_zip, find

class ImportTests(unittest.TestCase):
    def test_in_memory_import_skips_hidden_and_non_markdown(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('.obsidian/config', 'private settings')
            archive.writestr('../escape.md', 'escape')
            archive.writestr('Engineering/Grinding.md', 'Grinding wheel dressing: [[Machine Limits]]')
            archive.writestr('secrets.txt', 'secret')
        notes = load_markdown_zip(buffer.getvalue())
        self.assertEqual(list(notes), ['Engineering/Grinding.md'])
        self.assertEqual(find(notes, 'dressing')[0]['path'], 'Engineering/Grinding.md')
