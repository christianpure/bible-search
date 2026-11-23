"""Christian Pure's own data, fetched from christianpure.com once and kept on this computer.

The prayers and the article list are Christian Pure's (see data/seed/NOTICE). The repository carries a snapshot in
data/seed/packs; the app copies it on first start and refreshes it from christianpure.com once a week when it can. Nothing about
the person using the app is sent: the requests carry no cookies, no account and no search words.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
import urllib.request

UA = 'ChristianPureBibleSearch/0.1 (+https://christianpure.com)'
SOURCES = {
    'prayers-finder.json': 'https://christianpure.com/wp-content/mu-plugins/christianpure-prayer-offer/finder/prayers.json',
    'prayers-aloud.json': 'https://christianpure.com/wp-json/christianpure-app/v1/prayers-aloud',
    'llms.txt': 'https://christianpure.com/llms.txt',
}


def fetch(dest: pathlib.Path, force: bool = False, max_age_days: float = 7, log=print) -> dict[str, bool]:
    """Download each pack that is missing or older than a week. A failed download keeps the copy already here
    (the repository and every image carry a snapshot), so the app never depends on the network. Returns {file: present}."""
    dest.mkdir(parents=True, exist_ok=True)
    have = {}
    for name, url in SOURCES.items():
        path = dest / name
        if path.exists() and not force and time.time() - path.stat().st_mtime < max_age_days * 86400:
            have[name] = True
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            if name.endswith('.json'):
                json.loads(body)  # refuse a page that is not the data, such as a "checking your browser" page
            elif not body.startswith(b'# Christian Pure'):
                raise ValueError('not the article list')
            tmp = path.with_suffix(path.suffix + '.part')
            tmp.write_bytes(body)
            tmp.replace(path)
            have[name] = True
            log(f'Saved {name} from christianpure.com')
        except Exception as e:  # offline, blocked or changed: the app still runs on the Bible and topics
            have[name] = path.exists()
            log(f'Could not fetch {name} ({e.__class__.__name__}); {"using the saved copy" if path.exists() else "skipping it"}')
    return have


def prayers(dest: pathlib.Path):
    """Yield dicts: id, title, text, source, url, tags."""
    f = dest / 'prayers-finder.json'
    if f.exists():
        d = json.loads(f.read_text(encoding='utf-8'))
        facing, who = d.get('facing', {}), d.get('who', {})
        tags_for: dict[str, set[str]] = {}
        for pair, v in d.get('pairs', {}).items():
            fk, _, wk = pair.partition('/')
            for pid in v.get('ids', []):
                tags_for.setdefault(pid, set()).update([facing.get(fk, ''), who.get(wk, '')])
        for pid, p in d.get('prayers', {}).items():
            yield dict(id='f' + pid, title=p.get('t', ''), text=p.get('x', ''), source=p.get('a', ''),
                       url=p.get('u', ''), tags=' '.join(sorted(t for t in tags_for.get(pid, ()) if t)))
    f = dest / 'prayers-aloud.json'
    if f.exists():
        d = json.loads(f.read_text(encoding='utf-8'))
        occ = {o['key']: o for o in d.get('occasions', [])}
        for p in d.get('pieces', []):
            o = occ.get(p.get('occasion'), {})
            moment = next((m['label'] for m in o.get('moments', []) if m['key'] == p.get('moment')), '')
            title = f"{o.get('label', 'Prayer')}: {moment.lower()}" if moment else o.get('label', 'Prayer')
            source = re.sub(r'^From our article:\s*', '', p.get('source', ''))
            yield dict(id=f"a{p['id']}", title=title, text=p.get('text', ''), source=source, url=p.get('url', ''),
                       tags=f"{o.get('label', '')} {p.get('aloud', '')} prayer to read aloud")


LINK = re.compile(r'^- \[(.+?)\]\((https://christianpure\.com/[^)\s]+?)(?:\.md)?\)\s*(?::\s*(.*))?$')


def articles(dest: pathlib.Path):
    """Yield dicts: title, url, category, note, from llms.txt."""
    f = dest / 'llms.txt'
    if not f.exists():
        return
    category = ''
    seen = set()
    for line in f.read_text(encoding='utf-8').splitlines():
        if line.startswith('## ') or line.startswith('### '):
            category = line.lstrip('#').strip()
            continue
        m = LINK.match(line.strip())
        if not m:
            continue
        url = m.group(2)
        if url.endswith('.md'):
            url = url[:-3]
        if not url.endswith('/'):
            url += '/'
        if url in seen:
            continue
        seen.add(url)
        yield dict(title=m.group(1), url=url, category=category, note=(m.group(3) or '').strip())
