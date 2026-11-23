#!/usr/bin/env python3
"""Maintainers only: rebuild data/src/ from the open sources.

    python3 -I tools/make_sources.py BSB_JSON TOPICS_CSV

BSB_JSON    the Berean Standard Bible as one file, https://bible.helloao.org/api/BSB/complete.json (public domain)
TOPICS_CSV  Christian Pure's topical-bible.csv: OpenBible.info's topic votes (CC BY 4.0) with the verses picked on
            Christian Pure's verse pages first

Writes data/src/bsb.tsv.gz (osis, chapter, verse, text) and data/src/topics.tsv.gz
(topic, key, osis range, source, score, page). The app builds its search index from these on first start.
"""
from __future__ import annotations

import csv
import gzip
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from study.books import BY_USFM  # noqa: E402


def flatten(parts) -> str:
    out = []
    for p in parts:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            if 'text' in p and isinstance(p['text'], str):
                out.append(p['text'])
            if p.get('lineBreak'):
                out.append(' ')
    text = re.sub(r'\s+', ' ', ' '.join(out)).replace(' ,', ',').replace(' .', '.').strip()
    # The source puts a space before a closing quote that follows punctuation ("heel. ”"); close it up.
    return re.sub(r'([.,?!;:]) ([”’])', r'\1\2', text)


def bible(src: pathlib.Path, dest: pathlib.Path) -> int:
    d = json.loads(src.read_text(encoding='utf-8'))
    n = 0
    with gzip.open(dest, 'wt', encoding='utf-8', compresslevel=9) as f:
        for book in d['books']:
            osis = BY_USFM[book['id']][0]
            for c in book['chapters']:
                ch = c['chapter']['number']
                for item in c['chapter']['content']:
                    if item.get('type') != 'verse':
                        continue
                    text = flatten(item['content'])
                    if text:
                        f.write(f"{osis}\t{ch}\t{item['number']}\t{text}\n")
                        n += 1
    return n


def topics(src: pathlib.Path, dest: pathlib.Path) -> int:
    n = 0
    with open(src, newline='', encoding='utf-8') as fin, gzip.open(dest, 'wt', encoding='utf-8', compresslevel=9) as f:
        for row in csv.DictReader(fin):
            page = row['christianpure_page'].strip()
            f.write('\t'.join([row['topic'], row['topic_key'], row['osis'], row['source'],
                               row['openbible_score'] or '0', page]) + '\n')
            n += 1
    return n


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    out = ROOT / 'data' / 'src'
    out.mkdir(parents=True, exist_ok=True)
    print('verses', bible(pathlib.Path(sys.argv[1]), out / 'bsb.tsv.gz'))
    print('topic rows', topics(pathlib.Path(sys.argv[2]), out / 'topics.tsv.gz'))
