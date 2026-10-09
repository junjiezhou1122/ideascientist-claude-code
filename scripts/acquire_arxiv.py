#!/usr/bin/env python3
"""Acquire one registered exact arXiv PDF. Emit only a cache receipt, never content."""

import datetime as dt
import hashlib
import http.client
import json
import multiprocessing
import os
import re
import signal
import stat
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import NamedTuple

MAX_REQUEST_BYTES = 16384
MAX_RECEIPT_BYTES = 65536
MAX_STATE_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 40 * 1024 * 1024
SOCKET_SECONDS = 15
TOTAL_SECONDS = 60
EXACT_URL = re.compile(r'https://arxiv\.org/abs/((?:[0-9]{4}\.[0-9]{4,5}|[a-z][a-z0-9.-]*/[0-9]{7})(v[1-9][0-9]{0,3}))')
IDENTITY_FIELDS = {'title', 'authors', 'url', 'doi', 'version', 'publication_date', 'date_basis'}
RECEIPT_FIELDS = {'status', 'paper_id', 'identity', 'local_path', 'source_url', 'resolved_url', 'sha256', 'byte_size', 'pdf_magic', 'acquired_at', 'reused'}


class Request(NamedTuple):
    paper_id: str
    identity: dict
    source_url: str
    pdf: Path
    receipt: Path


def check_path(path, directory=False, missing=False):
    for parent in reversed(path.parents):
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError('Source path has a symlink or non-directory ancestor.')
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        if missing:
            return False
        raise ValueError('Required file is missing.') from None
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise ValueError('Source path must be a regular file or directory, without symlinks.')
    return True


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are unsupported.')
        result[key] = value
    return result


def read_json(path, maximum):
    check_path(path)
    with open(path, 'rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('JSON input exceeds the byte limit.')
    try:
        return json.loads(data, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError('Malformed JSON input.') from None


def date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('Expected a bibliographic date in YYYY-MM-DD format.')
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise ValueError('Invalid bibliographic date.') from None


def parse_request(argument):
    if not isinstance(argument, str) or len(argument) > 4096:
        raise ValueError('Supply one absolute sources/Pnnn.request.json path.')
    path = Path(argument)
    if not path.is_absolute() or str(path) != argument or '..' in path.parts:
        raise ValueError('Request path must be absolute and canonical.')
    match = re.fullmatch(r'(P[0-9]{3,})\.request\.json', path.name)
    if path.parent.name != 'sources' or not match or int(match[1][1:]) < 1 or match[1] != f'P{int(match[1][1:]):03d}':
        raise ValueError('Request must be sources/Pnnn.request.json for a canonical P ID.')
    check_path(path.parent, directory=True)
    request = read_json(path, MAX_REQUEST_BYTES)
    if not isinstance(request, dict) or set(request) != {'paper_id', 'identity'} or request['paper_id'] != match[1]:
        raise ValueError('Request must contain only matching paper_id and identity.')
    identity = request['identity']
    if not isinstance(identity, dict) or set(identity) != IDENTITY_FIELDS:
        raise ValueError('Request requires a complete bibliographic identity.')
    if any(not isinstance(identity[field], str) or not identity[field].strip() for field in ('title', 'url', 'version', 'date_basis')):
        raise ValueError('Identity text fields must be nonempty strings.')
    if not isinstance(identity['authors'], list) or not identity['authors'] or any(not isinstance(author, str) or not author.strip() for author in identity['authors']):
        raise ValueError('Identity requires named authors.')
    if identity['doi'] is not None and (not isinstance(identity['doi'], str) or not re.fullmatch(r'10\.[0-9]{4,9}/\S+', identity['doi'])):
        raise ValueError('Identity DOI is invalid.')
    exact = EXACT_URL.fullmatch(identity['url'])
    if not exact or identity['version'] not in (exact[2], f'arXiv {exact[1]}'):
        raise ValueError('Only a canonical HTTPS arXiv abs URL with a matching exact version is supported.')
    published = identity['publication_date']
    if published is not None:
        date(published)
    elif 'unknown' not in identity['date_basis'].lower():
        raise ValueError('An unknown publication date requires date_basis unknown.')
    run = read_json(path.parent.parent / 'run.json', MAX_STATE_BYTES)
    if not isinstance(run, dict) or 'cutoff' not in run or not isinstance(run.get('papers'), list):
        raise ValueError('Run must supply registered papers and cutoff.')
    registered = [paper for paper in run['papers'] if isinstance(paper, dict) and paper.get('paper_id') == match[1]]
    if len(registered) != 1 or registered[0].get('identity') != identity:
        raise ValueError('Request must exactly match one registered paper identity.')
    cutoff = run['cutoff']
    if cutoff is not None and (published is None or date(published) > date(cutoff)):
        raise ValueError('Exact version has an unknown or post-cutoff date.')
    return Request(match[1], identity, f'https://arxiv.org/pdf/{exact[1]}', path.parent / f'{match[1]}.pdf', path.parent / f'{match[1]}.acquisition.json')


def pdf_metadata(path):
    check_path(path)
    digest = hashlib.sha256()
    size = 0
    with open(path, 'rb') as stream:
        if stream.read(5) != b'%PDF-':
            raise ValueError('Source does not have PDF magic.')
        stream.seek(0)
        while chunk := stream.read(65536):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                raise ValueError('PDF exceeds the forty MiB limit.')
            digest.update(chunk)
    return {'sha256': digest.hexdigest(), 'byte_size': size, 'pdf_magic': True}


def reuse(request):
    pdf_exists = check_path(request.pdf, missing=True)
    receipt_exists = check_path(request.receipt, missing=True)
    if not pdf_exists and not receipt_exists:
        return None
    if not pdf_exists or not receipt_exists:
        raise ValueError('Incomplete cache pair is preserved; acquisition cannot overwrite it.')
    receipt = read_json(request.receipt, MAX_RECEIPT_BYTES)
    expected = {'status': 'ready', 'paper_id': request.paper_id, 'identity': request.identity, 'local_path': str(request.pdf), 'source_url': request.source_url, 'resolved_url': request.source_url, 'reused': False, **pdf_metadata(request.pdf)}
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS or any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError('Existing cache pair does not match the registered identity and PDF bytes.')
    if type(receipt['byte_size']) is not int or type(receipt['reused']) is not bool or not isinstance(receipt['acquired_at'], str):
        raise ValueError('Existing receipt has invalid metadata types.')
    try:
        timestamp = dt.datetime.fromisoformat(receipt['acquired_at'])
        if timestamp.tzinfo is None:
            raise ValueError
    except ValueError:
        raise ValueError('Existing receipt has an invalid acquisition date.') from None
    return dict(receipt, reused=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('PDF redirects are unsupported.')


def download(url, target):
    request = urllib.request.Request(url, headers={'Accept': 'application/pdf', 'Accept-Encoding': 'identity', 'User-Agent': 'IdeaScientist exact PDF acquisition'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=SOCKET_SECONDS) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError('PDF response requires HTTP 200 at the fixed exact URL.')
        content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
        if content_type not in ('application/pdf', 'application/octet-stream') or response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('PDF response has an unsupported content type or encoding.')
        length = response.headers.get('Content-Length')
        if length is not None and (not length.isascii() or not length.isdigit() or not 5 <= int(length) <= MAX_PDF_BYTES):
            raise ValueError('PDF response has an invalid or oversized content length.')
        check_path(target)
        descriptor = os.open(target, os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'wb') as stream:
            size = 0
            prefix = b''
            while chunk := response.read(65536):
                size += len(chunk)
                if size > MAX_PDF_BYTES:
                    raise ValueError('PDF exceeds the forty MiB limit.')
                prefix = (prefix + chunk)[:5]
                if len(prefix) == 5 and prefix != b'%PDF-':
                    raise ValueError('Source does not have PDF magic.')
                stream.write(chunk)
            if prefix != b'%PDF-' or (length is not None and size != int(length)):
                raise ValueError('PDF response is empty or truncated.')
            stream.flush()
            os.fsync(stream.fileno())


def _download_worker(url, target, connection):
    try:
        download(url, target)
        connection.send(True)
    except (ValueError, OSError, http.client.HTTPException):
        connection.send(False)
    finally:
        connection.close()


def run_download(url, target, deadline=None):
    context = multiprocessing.get_context('spawn')
    receiver, sender = context.Pipe(duplex=False)
    worker = context.Process(target=_download_worker, args=(url, target, sender))
    started = False
    try:
        worker.start()
        started = True
        sender.close()
        remaining = TOTAL_SECONDS if deadline is None else max(0, deadline - time.monotonic())
        if not receiver.poll(remaining):
            raise ValueError('PDF acquisition exceeded the total deadline.')
        try:
            completed = receiver.recv()
        except EOFError:
            completed = False
        if completed is not True:
            raise ValueError('Exact PDF acquisition failed; no usable cache was published.')
    finally:
        if started:
            if worker.is_alive():
                worker.terminate()
            worker.join(timeout=1)
            if worker.is_alive():
                worker.kill()
                worker.join()
            worker.close()
        sender.close()
        receiver.close()


def acquire(argument):
    deadline = time.monotonic() + TOTAL_SECONDS
    temporary = []
    request = None
    try:
        request = parse_request(argument)
        existing = reuse(request)
        if existing:
            return existing
        for _ in range(2):
            descriptor, name = tempfile.mkstemp(prefix=f'.acquire-{request.paper_id}-', dir=request.pdf.parent)
            os.close(descriptor)
            temporary.append(Path(name))
        run_download(request.source_url, temporary[0], deadline)
        receipt = {'status': 'ready', 'paper_id': request.paper_id, 'identity': request.identity, 'local_path': str(request.pdf), 'source_url': request.source_url, 'resolved_url': request.source_url, **pdf_metadata(temporary[0]), 'acquired_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'reused': False}
        with open(temporary[1], 'w', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        if time.monotonic() >= deadline:
            raise ValueError('PDF acquisition exceeded the total deadline.')
        check_path(request.pdf.parent, directory=True)
        os.link(temporary[0], request.pdf, follow_symlinks=False)
        os.link(temporary[1], request.receipt, follow_symlinks=False)
        return receipt
    except (ValueError, OSError, http.client.HTTPException) as error:
        reason = str(error) if isinstance(error, ValueError) else 'Exact PDF acquisition failed or cache publication was blocked; existing files are preserved.'
        result = {'status': 'blocked', 'reason': reason}
        if request is not None:
            result.update(paper_id=request.paper_id, identity=request.identity, local_path=str(request.pdf), source_url=request.source_url)
        return result
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)


def interrupt(signum, frame):
    raise KeyboardInterrupt


def main():
    signal.signal(signal.SIGTERM, interrupt)
    try:
        result = acquire(sys.argv[1]) if len(sys.argv) == 2 else {'status': 'blocked', 'reason': 'Supply exactly one absolute sources/Pnnn.request.json path.'}
    except KeyboardInterrupt:
        result = {'status': 'blocked', 'reason': 'PDF acquisition cancelled; child stopped and existing files preserved.'}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'ready' else 1


if __name__ == '__main__':
    raise SystemExit(main())
