import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_structure', ROOT / 'scripts/check_plugin.py')
structure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(structure)


class PluginTests(unittest.TestCase):
    def test_native_inventory_and_references(self):
        self.assertEqual(structure.check_plugin(), [])

    def copy_plugin(self, root):
        for directory in ('.claude-plugin', '.codex-plugin', '.agents', 'adapters', 'agents', 'skills', 'references', 'templates', 'scripts'):
            shutil.copytree(ROOT / directory, root / directory)
        shutil.copyfile(ROOT / 'package.json', root / 'package.json')

    def test_reader_has_acquisition_bash_but_cannot_gain_search_or_agent(self):
        reader_text = (ROOT / 'agents/paper-reader.md').read_text()
        self.assertIn('tools: Read, Write, Edit, WebFetch, Bash', reader_text)
        for tool in ('Agent', 'WebSearch'):
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.copy_plugin(root)
                reader = root / 'agents/paper-reader.md'
                reader.write_text(reader_text.replace('tools: Read, Write, Edit, WebFetch, Bash', f'tools: Read, Write, Edit, WebFetch, Bash, {tool}'))
                self.assertTrue(any('paper-reader.md: incorrect native tool boundary' in error for error in structure.check_plugin(root)))

    def test_fixed_acquisition_helper_must_ship(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_plugin(root)
            package_path = root / 'package.json'
            package = json.loads(package_path.read_text())
            self.assertIn('scripts/acquire_arxiv.py', package['files'])
            package['files'].remove('scripts/acquire_arxiv.py')
            package_path.write_text(json.dumps(package))
            self.assertTrue(any('acquisition:' in error for error in structure.check_plugin(root)))
            (root / 'scripts/acquire_arxiv.py').unlink()
            self.assertTrue(any('acquisition:' in error for error in structure.check_plugin(root)))


if __name__ == '__main__':
    unittest.main()
