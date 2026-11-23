"""Builds the search index (one SQLite file) from data/src and the saved Christian Pure packs."""
from __future__ import annotations

import gzip
import hashlib
import pathlib
import sqlite3

from . import packs
from .books import ORDER

SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE verses(id INTEGER PRIMARY KEY, osis TEXT, ch INT, v INT, text TEXT);
CREATE INDEX verses_ref ON verses(osis, ch, v);
CREATE VIRTUAL TABLE verses_fts USING fts5(text, content='verses', content_rowid='id', tokenize='porter unicode61');
CREATE TABLE topics(id INTEGER PRIMARY KEY, name TEXT, key TEXT UNIQUE, page TEXT, weight INT);
CREATE VIRTUAL TABLE topics_fts USING fts5(name, content='topics', content_rowid='id', tokenize='porter unicode61');
CREATE TABLE topic_verses(topic INT, osis TEXT, source TEXT, score INT, pos INT);
CREATE INDEX topic_verses_t ON topic_verses(topic, pos);
CREATE TABLE prayers(id INTEGER PRIMARY KEY, pid TEXT, title TEXT, text TEXT, source TEXT, url TEXT, tags TEXT);
CREATE VIRTUAL TABLE prayers_fts USING fts5(title, text, tags, content='prayers', content_rowid='id', tokenize='porter unicode61');
CREATE TABLE articles(id INTEGER PRIMARY KEY, title TEXT, url TEXT, category TEXT, note TEXT);
CREATE VIRTUAL TABLE articles_fts USING fts5(title, category, content='articles', content_rowid='id', tokenize='porter unicode61');
"""


def _stamp(src: pathlib.Path, pack_dir: pathlib.Path) -> str:
    h = hashlib.sha256(b'index v1')
    for f in sorted(list(src.glob('*.gz')) + list(pack_dir.glob('*'))):
        if f.is_file() and not f.name.endswith('.part'):
            st = f.stat()
            h.update(f'{f.name}:{st.st_size}:{int(st.st_mtime)}'.encode())
    return h.hexdigest()[:16]


def ensure(db_path: pathlib.Path, src: pathlib.Path, pack_dir: pathlib.Path, log=print) -> None:
    stamp = _stamp(src, pack_dir)
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as c:
                if c.execute("SELECT value FROM meta WHERE key='stamp'").fetchone() == (stamp,):
                    return
        except sqlite3.Error:
            pass
    log('Building the search index (about ten seconds, once)')
    tmp = db_path.with_suffix('.building')
    tmp.unlink(missing_ok=True)
    c = sqlite3.connect(tmp)
    c.executescript(SCHEMA)

    with gzip.open(src / 'bsb.tsv.gz', 'rt', encoding='utf-8') as f:
        rows = (line.rstrip('\n').split('\t') for line in f)
        c.executemany('INSERT INTO verses(osis, ch, v, text) VALUES (?,?,?,?)',
                      ((o, int(ch), int(v), t) for o, ch, v, t in rows))
    c.execute("INSERT INTO verses_fts(verses_fts) VALUES('rebuild')")

    topic_ids: dict[str, int] = {}
    pos: dict[int, int] = {}
    seen: set[tuple[int, str]] = set()
    with gzip.open(src / 'topics.tsv.gz', 'rt', encoding='utf-8') as f:
        for line in f:
            name, key, osis, source, score, page = line.rstrip('\n').split('\t')
            if osis.split('.')[0] not in ORDER:
                continue
            tid = topic_ids.get(key)
            if tid is None:
                tid = c.execute('INSERT INTO topics(name, key, page, weight) VALUES (?,?,?,0)', (name, key, page or None)).lastrowid
                topic_ids[key] = tid
            elif page:
                c.execute('UPDATE topics SET page=? WHERE id=? AND page IS NULL', (page, tid))
            if (tid, osis) in seen:
                continue
            seen.add((tid, osis))
            pos[tid] = pos.get(tid, 0) + 1
            c.execute('INSERT INTO topic_verses VALUES (?,?,?,?,?)', (tid, osis, source, int(score or 0), pos[tid]))
    # A topic's weight is the votes behind its verses: it settles ties between names that match a search equally.
    c.execute('UPDATE topics SET weight=(SELECT COALESCE(SUM(score),0) FROM topic_verses WHERE topic=topics.id)')
    c.execute("INSERT INTO topics_fts(topics_fts) VALUES('rebuild')")

    for p in packs.prayers(pack_dir):
        c.execute('INSERT INTO prayers(pid, title, text, source, url, tags) VALUES (?,?,?,?,?,?)',
                  (p['id'], p['title'], p['text'], p['source'], p['url'], p['tags']))
    c.execute("INSERT INTO prayers_fts(prayers_fts) VALUES('rebuild')")
    for a in packs.articles(pack_dir):
        c.execute('INSERT INTO articles(title, url, category, note) VALUES (?,?,?,?)',
                  (a['title'], a['url'], a['category'], a['note']))
    c.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")

    c.execute("INSERT INTO meta VALUES('stamp', ?)", (stamp,))
    c.commit()
    c.close()
    tmp.replace(db_path)
    log('Search index ready')
