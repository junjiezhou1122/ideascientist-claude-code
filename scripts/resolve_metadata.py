#!/usr/bin/env python3
"""Resolve one arXiv identity from public Atom metadata. Never emit source content."""

import datetime as dt
import http.client
import json
import queue
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MAX_BYTES = 262144
TIMEOUT_SECONDS = 20
IDENTIFIER = re.compile(r'(?:[0-9]{4}\.[0-9]{4,5}|[a-z][a-z0-9.-]*/[0-9]{7})(?:v[1-9][0-9]{0,3})?')
ATOM = '{http://www.w3.org/2005/Atom}'
API = 'https://export.arxiv.org/api/query'


def normalize_identifier(source):
    if not isinstance(source, str) or len(source) > 300:
        raise ValueError('Expected one arXiv ID or arXiv abs/pdf URL.')
    source = source.strip()
    if source.lower().startswith('arxiv:'):
        source = source[6:]
    if '://' in source:
        url = urllib.parse.urlsplit(source)
        if url.scheme not in ('http', 'https') or url.netloc not in ('arxiv.org', 'www.arxiv.org', 'export.arxiv.org') or url.query or url.fragment:
            raise ValueError('Only fixed arXiv abs/pdf URLs without query or fragment are supported.')
        if url.path.startswith('/abs/'):
            source = url.path[5:]
        elif url.path.startswith('/pdf/'):
            source = url.path[5:].removesuffix('.pdf')
        else:
            raise ValueError('Expected an arXiv abs/pdf URL.')
    if not IDENTIFIER.fullmatch(source):
        raise ValueError('Invalid arXiv identifier.')
    return source


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Metadata endpoint redirect is unsupported.')


def fetch_metadata(identifier):
    query = urllib.parse.urlencode({'id_list': identifier, 'max_results': 1})
    request = urllib.request.Request(f'{API}?{query}', headers={'Accept': 'application/atom+xml', 'User-Agent': 'IdeaScientist/0.2.1'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=TIMEOUT_SECONDS) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Metadata response exceeds the byte limit.')
    return data


def parse_metadata(data, requested):
    requested = normalize_identifier(requested)
    if len(data) > MAX_BYTES or b'<!DOCTYPE' in data.upper():
        raise ValueError('Oversized or unsupported XML metadata.')
    try:
        feed = ET.fromstring(data)
    except (ET.ParseError, LookupError) as error:
        raise ValueError('Malformed Atom metadata.') from error
    entries = feed.findall(f'{ATOM}entry')
    if feed.tag != f'{ATOM}feed' or len(entries) != 1:
        raise ValueError('Expected exactly one arXiv metadata record.')
    entry = entries[0]

    def text(tag, maximum=2000):
        value = ' '.join((entry.findtext(f'{ATOM}{tag}') or '').split())
        if not value or len(value) > maximum:
            raise ValueError(f'Missing or oversized metadata field {tag}.')
        return value

    returned = normalize_identifier(text('id', 300))
    match = re.fullmatch(r'(.+)v([1-9][0-9]{0,3})', returned)
    if not match:
        raise ValueError('Returned record has no exact version.')
    base, version = match.groups()
    if re.sub(r'v[1-9][0-9]{0,3}$', '', requested) != base or ('v' in requested.rsplit('/', 1)[-1] and returned != requested):
        raise ValueError('Returned identity does not match the requested base and exact version.')
    authors = [' '.join((author.findtext(f'{ATOM}name') or '').split()) for author in entry.findall(f'{ATOM}author')]
    if not authors or len(authors) > 300 or any(not author or len(author) > 500 for author in authors):
        raise ValueError('Missing or oversized author metadata.')
    date_field = 'published' if version == '1' else 'updated'
    timestamp = text(date_field, 40)
    try:
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', timestamp):
            raise ValueError
        date = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date().isoformat()
    except ValueError as error:
        raise ValueError(f'Invalid exact-version {date_field} date.') from error
    doi = entry.findtext('{http://arxiv.org/schemas/atom}doi')
    if doi is not None:
        doi = doi.strip()
        if not re.fullmatch(r'10\.[0-9]{4,9}/\S{1,200}', doi):
            raise ValueError('Invalid DOI metadata.')
    return {'status': 'resolved', 'identity': {
        'title': text('title'), 'authors': authors, 'url': f'https://arxiv.org/abs/{returned}',
        'doi': doi, 'version': f'v{version}', 'publication_date': date,
        'date_basis': f'arXiv Atom {date_field} for returned exact version {returned}',
    }, 'provenance': {'provider': 'arXiv Atom API', 'requested_id': requested, 'returned_id': returned, 'metadata_url': f'{API}?{urllib.parse.urlencode({"id_list": requested, "max_results": 1})}'}}


def resolve_metadata(source):
    try:
        identifier = normalize_identifier(source)
        return parse_metadata(fetch_metadata(identifier), identifier)
    except (ValueError, OSError, http.client.HTTPException) as error:
        return {'status': 'blocked', 'reason': str(error)[:500] or 'Metadata resolution failed.'}


def main():
    if len(sys.argv) != 2:
        result = {'status': 'blocked', 'reason': 'Supply exactly one arXiv ID or abs/pdf URL.'}
    else:
        completed = queue.Queue(maxsize=1)
        worker = threading.Thread(target=lambda: completed.put(resolve_metadata(sys.argv[1])), daemon=True)
        worker.start()
        try:
            result = completed.get(timeout=TIMEOUT_SECONDS)
        except queue.Empty:
            result = {'status': 'blocked', 'reason': 'Metadata resolution exceeded twenty seconds.'}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'resolved' else 1


if __name__ == '__main__':
    raise SystemExit(main())
