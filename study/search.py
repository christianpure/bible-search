"""Turns what a person types into verses, a prayer and Christian Pure pages, all from the local index."""
from __future__ import annotations

import re
import sqlite3
import urllib.parse

from .books import BY_OSIS, ORDER, parse_ref, ref_label

LEAD = re.compile(
    r"^(?:what\s+(?:does|do|did)\s+(?:the\s+)?(?:bible|scripture|god|jesus)\s+(?:say|teach|tell us)\s+(?:about|on|regarding)"
    r"|(?:some\s+)?(?:bible\s+)?(?:verses?|scriptures?|passages?)\s+(?:about|on|for|when)"
    r"|(?:a\s+)?(?:short\s+)?prayers?\s+(?:for|about|when|before|after|to)"
    r"|(?:i\s+(?:am|feel|'m)|i'm|im|feeling|how\s+(?:do|can|should)\s+i|help\s+me(?:\s+with)?|what\s+(?:is|are))"
    r")\s+", re.I)
STOP = set("""a an and are as at be been being but by can could did do does for from had has have how i if in into is it
its me my of on or our so than that the their them then there these they this to too us was we were what when where which
who why will with would you your about bible verse verses scripture say says god please""".split())


def _terms(q: str) -> list[str]:
    q = q.strip().strip('?!.').strip()
    for _ in range(2):
        q = LEAD.sub('', q)
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", q.lower())
    return [w.replace("'", '') for w in words if w not in STOP and len(w) > 1][:8]


# Words people type for the same need. Each term searches with its neighbours, so "sick" finds "illness".
NEAR = [
    'sick ill illness sickness healing heal surgery hospital',
    'worry worried worries anxious anxiety fear afraid',
    'sad sadness grief grieving mourning loss',
    'lonely loneliness alone',
    'money finances financial debt bills job work',
    'husband wife spouse marriage married',
    'child children son daughter kids',
    'mother mom mum father dad parent parents',
    'friend friends',
    'death dying died funeral',
    'thanks thankful thanksgiving grateful gratitude',
    'meal food dinner lunch breakfast grace',
]
_NEAR = {w: line.split() for line in NEAR for w in line.split()}


def _fts(terms: list[str], op: str = ' ') -> str:
    groups = []
    for t in terms:
        alts = _NEAR.get(t, [t])
        groups.append('(' + ' OR '.join(f'"{a}"' for a in alts) + ')' if len(alts) > 1 else f'"{t}"')
    return op.join(groups)


def parse_osis(span: str):
    """'Exod.20.1-Exod.20.26' -> ('Exod', 20, 1, 20, 26); 'Ps.23' -> ('Ps', 23, None, 23, None)."""
    a, _, b = span.partition('-')
    pa = a.split('.')
    pb = (b or a).split('.')
    if pa[0] not in BY_OSIS:
        return None
    c1 = int(pa[1]) if len(pa) > 1 else 1
    v1 = int(pa[2]) if len(pa) > 2 else None
    c2 = int(pb[1]) if len(pb) > 1 else c1
    v2 = int(pb[2]) if len(pb) > 2 else v1
    return pa[0], c1, v1, c2, v2


def passage(c: sqlite3.Connection, osis: str, c1: int, v1, c2: int, v2, cap: int = 6) -> dict:
    if v1 is None:
        rows = c.execute('SELECT ch, v, text FROM verses WHERE osis=? AND ch BETWEEN ? AND ? ORDER BY ch, v',
                         (osis, c1, c2)).fetchall()
    else:
        rows = c.execute('SELECT ch, v, text FROM verses WHERE osis=? AND (ch*1000+v) BETWEEN ? AND ? ORDER BY ch, v',
                         (osis, c1 * 1000 + v1, c2 * 1000 + (v2 or v1))).fetchall()
    shown = rows[:cap] if cap else rows
    label = ref_label(osis, c1, v1, v2, c2) if v1 is not None else ref_label(osis, c1, None)
    return dict(ref=label, osis=osis, chapter=c1, more=len(rows) - len(shown),
                verses=[dict(ch=r[0], v=r[1], text=r[2]) for r in shown])


def site_link(url: str, source: str) -> str:
    """Every link to christianpure.com says which store the app came from, and nothing about the person."""
    if not url:
        return url
    parts = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qsl(parts.query)
    q += [('utm_source', source), ('utm_medium', 'app'), ('utm_campaign', 'bible-search-app')]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


def search(c: sqlite3.Connection, query: str, source: str = 'github') -> dict:
    query = (query or '').strip()[:200]
    out: dict = dict(query=query, wants='prayer' if re.match(r'^\s*(?:a\s+)?(?:short\s+)?pray', query, re.I) else 'verses',
                     reference=None, topic=None, related=[], prayers=[], pages=[], matches=[])
    if not query:
        return out

    ref = parse_ref(query)
    if ref:
        osis, ch, v1, v2 = ref
        p = passage(c, osis, ch, v1, ch, v2, cap=0)
        if p['verses']:
            p['chapters'] = BY_OSIS[osis][3]
            out['reference'] = p
            return out

    terms = _terms(query)
    if not terms:
        return out

    # The subject: an exact name first, then every word, then any word, weighted by the votes behind it.
    key = '-'.join(terms)
    rows = c.execute('SELECT id, name, page FROM topics WHERE key=? OR lower(name)=?', (key, ' '.join(terms))).fetchall()
    for match in (_fts(terms), _fts(terms, ' OR ')):
        if len(rows) >= 6:
            break
        try:
            rows += [r for r in c.execute(
                'SELECT t.id, t.name, t.page FROM topics_fts f JOIN topics t ON t.id=f.rowid WHERE topics_fts MATCH ? '
                'ORDER BY bm25(topics_fts) - (t.page IS NOT NULL) * 2 - min(t.weight, 400) / 200.0 LIMIT 8',
                (match,)).fetchall() if r not in rows]
        except sqlite3.OperationalError:
            pass
    if rows:
        tid, name, page = rows[0]
        verses, taken = [], []
        for osis, src in c.execute('SELECT osis, source FROM topic_verses WHERE topic=? '
                                   "ORDER BY (source='Christian Pure') DESC, score DESC, pos LIMIT 20", (tid,)):
            span = parse_osis(osis)
            if not span:
                continue
            b, c1, v1, c2, v2 = span
            lo, hi = c1 * 1000 + (v1 or 0), c2 * 1000 + (v2 or 999)
            # A passage that overlaps or touches one already shown adds nothing new.
            if any(b == tb and lo <= thi + 1 and hi >= tlo - 1 for tb, tlo, thi in taken):
                continue
            p = passage(c, *span)
            if p['verses']:
                verses.append(p)
                taken.append((b, lo, hi))
            if len(verses) == 8:
                break
        out['topic'] = dict(name=name, page=site_link(page, source) if page else None, passages=verses)
        # Close subjects, without the ones that are only another form of a word already shown (worry, worries).
        def stem(n: str) -> str:
            out = []
            for w in n.lower().split():
                if w in ('being', 'feeling', 'feel', 'a', 'the'):
                    continue
                w = re.sub(r'(ies|ied)$', 'y', w)
                w = re.sub(r'(ness|ing|ed|es|s)$', '', w)
                out.append(re.sub(r'[ye]$', '', w))
            return ' '.join(out)
        shown, related = {stem(name)}, []
        for r in rows[1:]:
            k = stem(r[1])
            if k not in shown:
                shown.add(k)
                related.append(r[1])
        out['related'] = related[:5]

    # Prayers: every word if possible, else any word.
    for match in (_fts(terms), _fts(terms, ' OR ')):
        try:
            got = c.execute('SELECT p.title, p.text, p.source, p.url FROM prayers_fts f JOIN prayers p ON p.id=f.rowid '
                            'WHERE prayers_fts MATCH ? ORDER BY bm25(prayers_fts, 4.0, 1.0, 3.0) LIMIT 10', (match,)).fetchall()
            titles: set[str] = set()
            got = [g for g in got if not (g[0] in titles or titles.add(g[0]))][:3]
        except sqlite3.OperationalError:
            got = []
        if got:
            out['prayers'] = [dict(title=t, text=x, source=s, url=site_link(u, source)) for t, x, s, u in got]
            break

    for match in (_fts(terms), _fts(terms, ' OR ')):
        try:
            got = c.execute('SELECT a.title, a.url, a.category FROM articles_fts f JOIN articles a ON a.id=f.rowid '
                            "WHERE articles_fts MATCH ? ORDER BY bm25(articles_fts, 1.0, 0.3) - (a.category='Bible Verses') "
                            'LIMIT 5', (match,)).fetchall()
        except sqlite3.OperationalError:
            got = []
        if got:
            out['pages'] = [dict(title=t, url=site_link(u, source), category=k) for t, u, k in got]
            break

    # Words in the text itself: always for a quoted phrase, otherwise when no subject was found.
    if query.startswith('"') or not out['topic']:
        phrase = query.strip('"') if query.startswith('"') else None
        match = f'"{phrase}"' if phrase else _fts(terms)
        try:
            for osis, ch, v, text in c.execute(
                    'SELECT v.osis, v.ch, v.v, v.text FROM verses_fts f JOIN verses v ON v.id=f.rowid '
                    'WHERE verses_fts MATCH ? ORDER BY rank LIMIT 12', (match,)):
                out['matches'].append(dict(ref=ref_label(osis, ch, v), osis=osis, chapter=ch, text=text))
        except sqlite3.OperationalError:
            pass
        out['matches'].sort(key=lambda m: (ORDER[m['osis']], m['chapter']))
    return out


def chapter(c: sqlite3.Connection, osis: str, ch: int) -> dict | None:
    if osis not in BY_OSIS or not (1 <= ch <= BY_OSIS[osis][3]):
        return None
    p = passage(c, osis, ch, None, ch, None, cap=0)
    p['chapters'] = BY_OSIS[osis][3]
    return p


def counts(c: sqlite3.Connection) -> dict:
    return {t: c.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('verses', 'topics', 'prayers', 'articles')}
