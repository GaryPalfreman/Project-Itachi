import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from app import vault

class VaultTests(unittest.TestCase):
    def test_path_containment_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(vault,'settings',replace(vault.settings,vault=Path(directory))):
                vault.write('engineering/Test.md','# Test')
                self.assertEqual(vault.read('engineering/Test.md'),'# Test')
                self.assertEqual(vault.search('Test')[0]['path'],'engineering/Test.md')
                with self.assertRaises(ValueError): vault.write('engineering/Test.md','Overwrite')
                with self.assertRaises(ValueError): vault.note_path('../escape.md')
                with self.assertRaises(ValueError): vault.note_path('note.txt')

    def test_wikilinks_resolve_only_existing_unambiguous_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(vault,'settings',replace(vault.settings,vault=Path(directory))):
                vault.write('Machines/Grinding.md', '# Grinding\n[[Processes/Dressing|dress]]\n[[Missing]]')
                vault.write('Processes/Dressing.md', '# Dressing\n[[Grinding#Tools]]')
                graph = vault.graph()
                self.assertEqual(len(graph['nodes']), 2)
                self.assertEqual({(e['source'], e['target']) for e in graph['edges']},
                    {('Machines/Grinding','Processes/Dressing'), ('Processes/Dressing','Machines/Grinding')})

if __name__=='__main__': unittest.main()
