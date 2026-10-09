import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('adapter_structure', ROOT / 'scripts/check_plugin.py')
structure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(structure)


class RuntimeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for directory in ('.claude-plugin', '.codex-plugin', '.agents', 'adapters', 'agents', 'skills', 'references', 'templates', 'scripts'):
            shutil.copytree(ROOT / directory, self.root / directory)
        shutil.copyfile(ROOT / 'package.json', self.root / 'package.json')

    def tearDown(self):
        self.temporary.cleanup()

    def test_unsupported_codex_agents_metadata_is_rejected(self):
        path = self.root / '.codex-plugin/plugin.json'
        manifest = json.loads(path.read_text())
        manifest['agents'] = './agents'
        path.write_text(json.dumps(manifest))
        self.assertIn('Codex: unsupported metadata or skills path', structure.check_plugin(self.root))

    def test_missing_cached_shared_role_is_rejected(self):
        (self.root / 'references/roles/paper-reader.md').unlink()
        self.assertIn('shared roles: canonical inventory mismatch', structure.check_plugin(self.root))

    def test_host_packages_are_not_bundled_dependencies(self):
        path = self.root / 'package.json'
        package = json.loads(path.read_text())
        package['dependencies'] = package['peerDependencies']
        path.write_text(json.dumps(package))
        self.assertIn('Pi: host packages must remain peer dependencies', structure.check_plugin(self.root))

    def test_wrapper_cannot_silently_drop_canonical_reader(self):
        path = self.root / 'agents/paper-reader.md'
        path.write_text(path.read_text().replace('references/roles/paper-reader.md', 'references/contracts.md'))
        self.assertIn('paper-reader: Claude wrapper missing canonical role', structure.check_plugin(self.root))

    def test_versions_are_synchronized(self):
        path = self.root / '.codex-plugin/plugin.json'
        manifest = json.loads(path.read_text())
        manifest['version'] = '999.0.0'
        path.write_text(json.dumps(manifest))
        self.assertIn('manifests: versions differ', structure.check_plugin(self.root))


if __name__ == '__main__':
    unittest.main()
