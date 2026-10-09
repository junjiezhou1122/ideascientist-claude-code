import importlib.util
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

    def test_reader_cannot_gain_search_or_agent_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ('.claude-plugin', 'agents', 'skills', 'references', 'templates', 'scripts'):
                shutil.copytree(ROOT / directory, root / directory)
            reader = root / 'agents/paper-reader.md'
            reader.write_text(reader.read_text().replace('tools: Read, Write, Edit, WebFetch', 'tools: Read, Write, Edit, WebFetch, Agent'))
            self.assertTrue(any('paper-reader.md: incorrect native tool boundary' in error for error in structure.check_plugin(root)))


if __name__ == '__main__':
    unittest.main()
