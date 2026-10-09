import copy
import hashlib
import json
import multiprocessing
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import acquire_arxiv as acquisition

PDF = b'%PDF-1.7\nprivate paper body that must never enter stdout\n%%EOF\n'
URL = 'https://arxiv.org/pdf/2501.12345v1'
IDENTITY = {'title': 'Exact paper', 'authors': ['Author'], 'url': 'https://arxiv.org/abs/2501.12345v1', 'doi': None, 'version': 'v1', 'publication_date': '2025-01-20', 'date_basis': 'arXiv Atom published for exact v1'}


class Response:
    def __init__(self, body=PDF, status=200, content_type='application/pdf', url=URL):
        self.body, self.status, self.url = body, status, url
        self.headers = {'Content-Type': content_type, 'Content-Length': str(len(body))}
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def geturl(self):
        return self.url

    def read(self, size):
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


def failed_worker(url, target, connection):
    Path(target).write_bytes(b'paper body partial')
    connection.send(False)
    connection.close()


def endless_writer(url, target, connection):
    with open(target, 'ab', buffering=0) as stream:
        while True:
            stream.write(b'x')
            time.sleep(0.01)


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.sources = self.root / 'sources'
        self.sources.mkdir()
        self.request = self.sources / 'P001.request.json'
        self.identity = copy.deepcopy(IDENTITY)
        self.run = {'cutoff': None, 'papers': [{'paper_id': 'P001', 'identity': self.identity}]}
        self.save()

    def tearDown(self):
        self.temporary.cleanup()

    def save(self, request=None):
        self.request.write_text(json.dumps(request or {'paper_id': 'P001', 'identity': self.identity}))
        (self.root / 'run.json').write_text(json.dumps(self.run))

    def acquire(self, response=None):
        opener = unittest.mock.Mock()
        opener.open.return_value = response or Response()
        with patch.object(acquisition, 'run_download', side_effect=lambda url, target, deadline: acquisition.download(url, target)), patch.object(acquisition.urllib.request, 'build_opener', return_value=opener):
            result = acquisition.acquire(str(self.request))
        return result, opener

    def test_success_is_metadata_only_and_independently_hashable(self):
        request_bytes = self.request.read_bytes()
        state_bytes = (self.root / 'run.json').read_bytes()
        result, opener = self.acquire()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['identity'], self.identity)
        self.assertEqual(result['source_url'], URL)
        self.assertEqual(result['resolved_url'], URL)
        self.assertEqual(Path(result['local_path']).read_bytes(), PDF)
        self.assertEqual(result['sha256'], hashlib.sha256(PDF).hexdigest())
        self.assertEqual(result['byte_size'], len(PDF))
        self.assertIs(result['pdf_magic'], True)
        self.assertFalse(result['reused'])
        self.assertNotIn('private paper body', json.dumps(result))
        self.assertEqual(set(result), acquisition.RECEIPT_FIELDS)
        self.assertEqual(json.loads((self.sources / 'P001.acquisition.json').read_text()), result)
        self.assertEqual(self.request.read_bytes(), request_bytes)
        self.assertEqual((self.root / 'run.json').read_bytes(), state_bytes)
        opener.open.assert_called_once()
        sent = opener.open.call_args.args[0]
        self.assertEqual(sent.full_url, URL)
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 15)

    def test_complete_pair_reuses_without_network_or_writes(self):
        self.acquire()
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.sources.iterdir()}
        with patch.object(acquisition, 'run_download', side_effect=AssertionError('network forbidden')):
            result = acquisition.acquire(str(self.request))
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(result['reused'])
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.sources.iterdir()})

    def test_near_limit_request_generates_reusable_larger_receipt(self):
        self.identity['title'] = 'A' * 15900
        self.save()
        self.assertLessEqual(self.request.stat().st_size, acquisition.MAX_REQUEST_BYTES)
        self.assertEqual(self.acquire()[0]['status'], 'ready')
        receipt = self.sources / 'P001.acquisition.json'
        self.assertGreater(receipt.stat().st_size, acquisition.MAX_REQUEST_BYTES)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.sources.iterdir()}
        with patch.object(acquisition, 'run_download', side_effect=AssertionError('network forbidden')):
            result = acquisition.acquire(str(self.request))
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(result['reused'])
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.sources.iterdir()})

    def test_invalid_requests_block_before_network(self):
        for change in [
            {'url': 'https://arxiv.org.evil/abs/2501.12345v1'},
            {'url': 'http://arxiv.org/abs/2501.12345v1'},
            {'url': 'https://arxiv.org/abs/2501.12345'},
            {'url': 'https://arxiv.org/abs/2501.12345v1?x=1'},
            {'url': 'https://arxiv.org/abs/2501.12345v1#page'},
            {'version': 'v2'}, {'version': 'latest'}, {'publication_date': '2025-99-99'},
        ]:
            with self.subTest(change=change):
                self.identity = dict(IDENTITY, **change)
                self.run['papers'][0]['identity'] = self.identity
                self.save()
                with patch.object(acquisition, 'run_download') as network:
                    self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
                    network.assert_not_called()
        self.assertEqual(list(self.sources.iterdir()), [self.request])

    def test_registration_cutoff_and_capability_mismatch(self):
        cases = [({'paper_id': 'P002', 'identity': IDENTITY}, self.run),
                 ({'paper_id': 'P001', 'identity': dict(IDENTITY, title='Different')}, self.run),
                 ({'paper_id': 'P001', 'identity': IDENTITY, 'destination': '/elsewhere'}, self.run),
                 ({'paper_id': 'P001', 'identity': IDENTITY}, dict(self.run, cutoff='2025-01-19')),
                 ({'paper_id': 'P001', 'identity': dict(IDENTITY, publication_date=None, date_basis='unknown')}, {'cutoff': '2025-02-01', 'papers': [{'paper_id': 'P001', 'identity': dict(IDENTITY, publication_date=None, date_basis='unknown')}]}),
                 ({'paper_id': 'P001', 'identity': IDENTITY}, dict(self.run, papers=self.run['papers'] * 2))]
        for request, run in cases:
            with self.subTest(request=request, run=run):
                self.run = run
                self.save(request)
                with patch.object(acquisition, 'run_download') as network:
                    self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
                    network.assert_not_called()

    def test_legacy_exact_version_and_unknown_live_date(self):
        self.identity.update(version='arXiv 2501.12345v1', publication_date=None, date_basis='unknown')
        self.save()
        self.assertEqual(self.acquire()[0]['status'], 'ready')

    def test_live_unknown_date_can_explain_its_basis(self):
        self.identity.update(publication_date=None, date_basis='Exact version date is unknown from available metadata.')
        self.save()
        self.assertEqual(self.acquire()[0]['status'], 'ready')

    def test_pdf_download_works_without_platform_nofollow_flag(self):
        flag = getattr(acquisition.os, 'O_NOFOLLOW', None)
        if flag is not None:
            delattr(acquisition.os, 'O_NOFOLLOW')
        try:
            self.assertEqual(self.acquire()[0]['status'], 'ready')
        finally:
            if flag is not None:
                acquisition.os.O_NOFOLLOW = flag

    def test_duplicate_keys_oversized_and_noncanonical_paths(self):
        for payload in ['{"paper_id":"P001","paper_id":"P001","identity":{}}', 'x' * (acquisition.MAX_REQUEST_BYTES + 1)]:
            self.request.write_text(payload)
            with patch.object(acquisition, 'run_download') as network:
                self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
                network.assert_not_called()
        self.save()
        for path in ['sources/P001.request.json', str(self.sources / 'P01.request.json'), str(self.sources / '..' / 'sources' / self.request.name)]:
            with patch.object(acquisition, 'run_download') as network:
                self.assertEqual(acquisition.acquire(path)['status'], 'blocked')
                network.assert_not_called()

    def test_symlinks_and_nonregular_files_block_without_network(self):
        self.request.unlink()
        original = self.root / 'original.json'
        original.write_text(json.dumps({'paper_id': 'P001', 'identity': IDENTITY}))
        self.request.symlink_to(original)
        with patch.object(acquisition, 'run_download') as network:
            self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
            network.assert_not_called()
        self.request.unlink()
        self.save()
        target = self.sources / 'P001.pdf'
        target.symlink_to(original)
        self.assertEqual(self.acquire()[0]['status'], 'blocked')
        self.assertTrue(target.is_symlink())
        target.unlink()
        target.mkdir()
        self.assertEqual(self.acquire()[0]['status'], 'blocked')
        target.rmdir()
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with patch.object(acquisition, 'run_download') as network:
            self.assertEqual(acquisition.acquire(str(alias / 'sources' / self.request.name))['status'], 'blocked')
            network.assert_not_called()
        state = self.root / 'run.json'
        saved = state.read_bytes()
        state.unlink()
        state.symlink_to(original)
        with patch.object(acquisition, 'run_download') as network:
            self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
            network.assert_not_called()
        state.unlink()
        state.write_bytes(saved)

    def test_orphan_and_tampered_pairs_preserve_bytes(self):
        for filename in ['P001.pdf', 'P001.acquisition.json']:
            path = self.sources / filename
            path.write_bytes(b'existing bytes')
            with patch.object(acquisition, 'run_download') as network:
                self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
                network.assert_not_called()
            self.assertEqual(path.read_bytes(), b'existing bytes')
            path.unlink()
        self.acquire()
        pdf = self.sources / 'P001.pdf'
        pdf.write_bytes(b'%PDF-tampered')
        receipt = self.sources / 'P001.acquisition.json'
        before = receipt.read_bytes()
        with patch.object(acquisition, 'run_download') as network:
            self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
            network.assert_not_called()
        self.assertEqual(pdf.read_bytes(), b'%PDF-tampered')
        self.assertEqual(receipt.read_bytes(), before)

    def test_receipt_mismatches_never_reuse_or_mutate_cache(self):
        self.acquire()
        receipt_path = self.sources / 'P001.acquisition.json'
        valid = json.loads(receipt_path.read_text())
        for field, value in [('identity', dict(IDENTITY, version='v2')), ('paper_id', 'P002'), ('local_path', '/other.pdf'), ('source_url', 'https://evil.invalid'), ('resolved_url', 'https://arxiv.org/pdf/2501.12345v2'), ('byte_size', len(PDF) + 1), ('sha256', '0' * 64), ('pdf_magic', 'html'), ('acquired_at', 'unknown'), ('reused', True), ('body', 'invented content')]:
            with self.subTest(field=field):
                receipt_path.write_text(json.dumps(dict(valid, **{field: value})))
                before = {p.name: p.read_bytes() for p in self.sources.iterdir()}
                with patch.object(acquisition, 'run_download') as network:
                    self.assertEqual(acquisition.acquire(str(self.request))['status'], 'blocked')
                    network.assert_not_called()
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.sources.iterdir()})

    def test_partial_publication_never_replaces_and_retains_orphan(self):
        real_link = acquisition.os.link
        def race(source, target, **kwargs):
            if str(target).endswith('.acquisition.json'):
                Path(target).write_bytes(b'racing receipt')
            real_link(source, target, **kwargs)
        with patch.object(acquisition.os, 'link', side_effect=race):
            result, _ = self.acquire()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual((self.sources / 'P001.pdf').read_bytes(), PDF)
        self.assertEqual((self.sources / 'P001.acquisition.json').read_bytes(), b'racing receipt')
        self.assertFalse(any(p.name.startswith('.acquire-') for p in self.sources.iterdir()))

    def test_bad_network_payloads_block_and_leave_no_cache(self):
        cases = [Response(status=201), Response(status=302), Response(content_type='text/html'), Response(body=b'not a pdf'), Response(url='https://evil.invalid/pdf')]
        for response in cases:
            with self.subTest(response=response):
                result, opener = self.acquire(response)
                self.assertEqual(result['status'], 'blocked')
                opener.open.assert_called_once()
                self.assertEqual(list(self.sources.iterdir()), [self.request])
        response = Response()
        del response.headers['Content-Length']
        with patch.object(acquisition, 'MAX_PDF_BYTES', len(PDF) - 1):
            self.assertEqual(self.acquire(response)[0]['status'], 'blocked')
        response = Response()
        response.headers['Content-Length'] = str(len(PDF) + 1)
        self.assertEqual(self.acquire(response)[0]['status'], 'blocked')
        self.assertEqual(list(self.sources.iterdir()), [self.request])

    def test_redirect_handler_rejects_without_following(self):
        with self.assertRaises(ValueError):
            acquisition.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid')

    def test_spawned_download_failure_returns_blocked_metadata_only(self):
        before = {p.pid for p in multiprocessing.active_children()}
        with patch.object(acquisition, '_download_worker', failed_worker):
            result = acquisition.acquire(str(self.request))
        self.assertEqual(result['status'], 'blocked')
        self.assertNotIn('paper body', json.dumps(result))
        self.assertEqual(list(self.sources.iterdir()), [self.request])
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)

    def test_cancellation_stops_child_before_temp_cleanup(self):
        from multiprocessing.connection import Connection
        original_poll = Connection.poll
        def cancel(connection, timeout):
            original_poll(connection, 0.2)
            raise KeyboardInterrupt
        before = {p.pid for p in multiprocessing.active_children()}
        with patch.object(acquisition, '_download_worker', endless_writer), patch.object(Connection, 'poll', side_effect=cancel, autospec=True):
            with self.assertRaises(KeyboardInterrupt):
                acquisition.acquire(str(self.request))
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)
        self.assertEqual(list(self.sources.iterdir()), [self.request])

    def test_deadline_terminates_and_joins_real_spawned_writer(self):
        target = self.sources / 'deadline.tmp'
        target.touch()
        before = {p.pid for p in multiprocessing.active_children()}
        with patch.object(acquisition, '_download_worker', endless_writer), patch.object(acquisition, 'TOTAL_SECONDS', 0.5):
            with self.assertRaises(ValueError):
                acquisition.run_download(URL, target)
        size = target.stat().st_size
        time.sleep(0.05)
        self.assertEqual(target.stat().st_size, size)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)


if __name__ == '__main__':
    unittest.main()
