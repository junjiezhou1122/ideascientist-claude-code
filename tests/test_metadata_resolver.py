"""Synthetic Atom records verify exact identity without fetching bodies or models."""

import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/resolve_metadata.py'


def atom(identifier='2310.10134v2', published='2023-10-15T12:00:00Z', updated='2024-01-02T12:00:00Z'):
    return f'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
    <id>http://arxiv.org/abs/{identifier}</id><title> Synthetic exact identity </title>
    <author><name>Fixture Author</name></author><published>{published}</published><updated>{updated}</updated>
    <summary>ABSTRACT_BODY_SENTINEL</summary></entry></feed>'''.encode()


class MetadataResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.is_file():
            raise AssertionError('The fixed arXiv metadata resolver is missing.')
        spec = importlib.util.spec_from_file_location('metadata_resolver', SCRIPT)
        cls.resolver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.resolver)

    def test_supported_identifiers_normalize_without_arbitrary_fetch(self):
        for source in ('2310.10134v2', 'arXiv:2310.10134v2', 'https://arxiv.org/abs/2310.10134v2', 'https://arxiv.org/pdf/2310.10134v2.pdf'):
            self.assertEqual(self.resolver.normalize_identifier(source), '2310.10134v2')
        self.assertEqual(self.resolver.normalize_identifier('https://arxiv.org/abs/hep-th/9901001v1'), 'hep-th/9901001v1')
        for source in ('https://evil.test/abs/2310.10134', 'https://arxiv.org.evil.test/abs/2310.10134', 'https://arxiv.org/abs/2310.10134?x=1', 'https://user@arxiv.org/abs/2310.10134', '2310.10134v0', '2310.10134;touch /tmp/x'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.resolver.normalize_identifier(source)

    def test_unversioned_selects_returned_version_and_revision_date(self):
        result = self.resolver.parse_metadata(atom(), '2310.10134')
        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(result['identity']['version'], 'v2')
        self.assertEqual(result['identity']['publication_date'], '2024-01-02')
        self.assertEqual(result['identity']['url'], 'https://arxiv.org/abs/2310.10134v2')
        self.assertNotIn('ABSTRACT_BODY_SENTINEL', json.dumps(result))
        self.assertEqual(set(result['identity']), {'title', 'authors', 'url', 'doi', 'version', 'publication_date', 'date_basis'})

    def test_v1_uses_published_date(self):
        result = self.resolver.parse_metadata(atom('2310.10134v1'), '2310.10134v1')
        self.assertEqual(result['identity']['publication_date'], '2023-10-15')

    def test_exact_requested_older_version_and_wrong_identity_block(self):
        for returned in ('2310.10134v2', '2310.99999v1', '2310.10134', 'https://evil.test/abs/2310.10134v1'):
            with self.subTest(returned=returned), self.assertRaises(ValueError):
                self.resolver.parse_metadata(atom(returned), '2310.10134v1')

    def test_incomplete_malformed_empty_and_oversized_records_block(self):
        records = [b'<feed>', b'<feed xmlns="http://www.w3.org/2005/Atom"/>', atom().replace(b'<author><name>Fixture Author</name></author>', b''), atom().replace(b'<title> Synthetic exact identity </title>', b''), atom(updated='2024-99-01T00:00:00Z'), atom() + b' ' * self.resolver.MAX_BYTES, atom().replace(b'</entry>', b'</entry><entry/>')]
        for record in records:
            with self.subTest(record=record[:60]), self.assertRaises(ValueError):
                self.resolver.parse_metadata(record, '2310.10134')

    def test_network_errors_return_blocked_json_and_no_writes(self):
        with patch.object(self.resolver, 'fetch_metadata', side_effect=OSError('offline')):
            result = self.resolver.resolve_metadata('2310.10134')
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(result['reason'])
        self.assertNotIn('identity', result)

    def test_fetch_uses_fixed_endpoint_byte_bound_and_no_redirects(self):
        resolver = self.resolver
        class Response(io.BytesIO):
            def read(self, size=-1):
                self.requested_size = size
                return super().read(size)
        response = Response(atom())
        with patch.object(resolver.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            result = resolver.fetch_metadata('2310.10134v2')
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://export.arxiv.org/api/query?id_list=2310.10134v2&max_results=1')
            self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 20)
            self.assertEqual(response.requested_size, resolver.MAX_BYTES + 1)
            self.assertEqual(result, atom())
            self.assertIs(opener.call_args.args[0], resolver.NoRedirect)
        with self.assertRaises(ValueError):
            resolver.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.test/metadata')
        with patch.object(resolver.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = Response(b'x' * (resolver.MAX_BYTES + 1))
            self.assertEqual(resolver.resolve_metadata('2310.10134')['status'], 'blocked')

    def test_invalid_input_never_requests_network(self):
        with patch.object(self.resolver, 'fetch_metadata') as fetch:
            self.assertEqual(self.resolver.resolve_metadata('https://evil.test/paper')['status'], 'blocked')
            fetch.assert_not_called()

    def test_cli_fixture_returns_metadata_without_source_or_run_writes(self):
        driver = '''import importlib.util,sys
spec=importlib.util.spec_from_file_location('resolver',sys.argv[1]); resolver=importlib.util.module_from_spec(spec); spec.loader.exec_module(resolver)
resolver.fetch_metadata=lambda identifier: sys.stdin.buffer.read()
sys.argv=[sys.argv[1], '2310.10134']; raise SystemExit(resolver.main())
'''
        result = subprocess.run([sys.executable, '-c', driver, str(SCRIPT)], input=atom(), capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['identity']['version'], 'v2')
        self.assertNotIn(b'ABSTRACT_BODY_SENTINEL', result.stdout)
        self.assertEqual(result.stderr, b'')

    def test_invalid_xml_encoding_and_http_status_return_blocked(self):
        records = [b'<?xml version="1.0" encoding="unknown-encoding"?><feed/>']
        for record in records:
            with patch.object(self.resolver, 'fetch_metadata', return_value=record):
                result = self.resolver.resolve_metadata('2310.10134')
            self.assertEqual(result['status'], 'blocked')
            self.assertNotIn('identity', result)
        with patch.object(self.resolver, 'fetch_metadata', side_effect=self.resolver.http.client.BadStatusLine('invalid status')):
            result = self.resolver.resolve_metadata('2310.10134')
        self.assertEqual(result['status'], 'blocked')
        self.assertNotIn('identity', result)

    def test_cli_timeout_exits_without_waiting_for_network_worker(self):
        driver = '''import importlib.util,sys,threading
spec=importlib.util.spec_from_file_location('resolver',sys.argv[1]); resolver=importlib.util.module_from_spec(spec); spec.loader.exec_module(resolver)
resolver.TIMEOUT_SECONDS=0.02
resolver.fetch_metadata=lambda identifier: threading.Event().wait(60)
sys.argv=[sys.argv[1], '2310.10134']; raise SystemExit(resolver.main())
'''
        result = subprocess.run([sys.executable, '-c', driver, str(SCRIPT)], capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
        self.assertIn('exceeded', json.loads(result.stdout)['reason'])
        self.assertEqual(result.stderr, '')

    def test_invalid_cli_is_bounded_blocked_json(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'https://evil.test/paper'], text=True, capture_output=True, timeout=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
        self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
