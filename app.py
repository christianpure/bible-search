#!/usr/bin/env python3
"""Christian Pure Bible Search: search the Bible and Christian Pure's prayers on your own computer.

    python3 app.py                 # http://127.0.0.1:8417
    HOST=0.0.0.0 PORT=8417 DATA_DIR=/data python3 app.py

Standard library only (Python 3.9 or newer with SQLite FTS5, as every python.org and Docker Python has).
"""
from __future__ import annotations

import json
import mimetypes
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from study import ai, db, packs, search  # noqa: E402

DATA = pathlib.Path(os.environ.get('DATA_DIR', ROOT / 'data' / 'local')).resolve()
SOURCE = os.environ.get('STUDY_SOURCE', 'github')  # which store the app came from, for links to christianpure.com
WEB = ROOT / 'web'
DB_PATH = DATA / 'study.db'
_local = threading.local()


def conn() -> sqlite3.Connection:
    c = getattr(_local, 'c', None)
    if c is None:
        c = _local.c = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True, check_same_thread=False)
    return c


def _writable(d: pathlib.Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / '.write-test'
        probe.write_text('ok')
        probe.unlink()
        return True
    except OSError:
        return False


def prepare(offline: bool = False) -> None:
    global DATA, DB_PATH
    # The data folder holds only the index and the saved packs, which can be rebuilt in a second, so a folder this
    # user cannot write (a NAS share owned by another user, say) is no reason to stop.
    if not _writable(DATA):
        fallback = pathlib.Path(tempfile.gettempdir()) / 'christianpure-bible-search'
        print(f'{DATA} is not writable; keeping the index in {fallback} instead', flush=True)
        DATA, DB_PATH = fallback, fallback / 'study.db'
        DATA.mkdir(parents=True, exist_ok=True)
    # An image carries the packs saved when it was built, so a new install works before it ever goes online.
    seed = pathlib.Path(os.environ.get('SEED_DIR', ROOT / 'data' / 'seed')) / 'packs'
    if seed.is_dir():
        (DATA / 'packs').mkdir(exist_ok=True)
        for f in seed.iterdir():
            if f.is_file() and not (DATA / 'packs' / f.name).exists():
                shutil.copy2(f, DATA / 'packs' / f.name)
    if not offline and os.environ.get('STUDY_OFFLINE', '') not in ('1', 'yes', 'true'):
        packs.fetch(DATA / 'packs')
    db.ensure(DB_PATH, ROOT / 'data' / 'src', DATA / 'packs')


class Handler(BaseHTTPRequestHandler):
    server_version = 'ChristianPureBibleSearch/0.1'

    def log_message(self, fmt, *args):  # no search words in the log
        pass

    def _send(self, code: int, body: bytes, ctype: str, cache: str = 'no-store') -> None:
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode(), 'application/json; charset=utf-8')

    def do_GET(self):  # noqa: N802
        u = urllib.parse.urlsplit(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == '/api/search':
            return self._json(search.search(conn(), q.get('q', ''), SOURCE))
        if u.path == '/api/chapter':
            try:
                p = search.chapter(conn(), q.get('book', ''), int(q.get('ch', '0')))
            except ValueError:
                p = None
            return self._json(p or {'error': 'No such chapter'}, 200 if p else 404)
        if u.path == '/api/status':
            return self._json(dict(ai=ai.status(), counts=search.counts(conn()), source=SOURCE))
        if u.path in ('/', '/index.html'):
            return self._file(WEB / 'index.html')
        if u.path == '/healthz':
            return self._send(200, b'ok', 'text/plain')
        target = (WEB / u.path.lstrip('/')).resolve()
        if WEB in target.parents and target.is_file():
            return self._file(target, cache='public, max-age=3600')
        self._send(404, b'Not found', 'text/plain')

    def do_POST(self):  # noqa: N802
        if urllib.parse.urlsplit(self.path).path != '/api/summary':
            return self._send(404, b'Not found', 'text/plain')
        try:
            n = min(int(self.headers.get('Content-Length', '0')), 4096)
            question = json.loads(self.rfile.read(n) or b'{}').get('q', '')[:200]
        except (ValueError, AttributeError):
            return self._json({'error': 'Send {"q": "..."}'}, 400)
        if not ai.status()['ready']:
            return self._json({'error': 'No AI model is running on this computer.'}, 503)
        try:
            text = ai.summarise(question, search.search(conn(), question, SOURCE))
        except Exception as e:
            return self._json({'error': f'The model stopped before it finished ({e.__class__.__name__}).'}, 502)
        self._json({'text': text, 'model': ai.MODEL})

    def _file(self, path: pathlib.Path, cache: str = 'no-cache') -> None:
        ctype = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript',):
            ctype += '; charset=utf-8'
        self._send(200, path.read_bytes(), ctype, cache)


def main() -> None:
    mimetypes.add_type('font/woff2', '.woff2')
    mimetypes.add_type('application/javascript', '.js')
    if '--prepare' in sys.argv:  # used when an image is built: fetch and index, then stop
        prepare()
        return
    prepare(offline='--offline' in sys.argv)
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8417'))
    httpd = ThreadingHTTPServer((host, port), Handler)
    shown = '127.0.0.1' if host in ('0.0.0.0', '::') else host
    print(f'Christian Pure Bible Search is running at http://{shown}:{port}', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
