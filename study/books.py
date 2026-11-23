"""The 66 books: OSIS code, USFM code, English name and the other names people type."""
from __future__ import annotations

import re

# (osis, usfm, name, chapters, extra names)
BOOKS = [
    ('Gen', 'GEN', 'Genesis', 50, 'gn ge'),
    ('Exod', 'EXO', 'Exodus', 40, 'ex exo'),
    ('Lev', 'LEV', 'Leviticus', 27, 'lv le'),
    ('Num', 'NUM', 'Numbers', 36, 'nm nu nb'),
    ('Deut', 'DEU', 'Deuteronomy', 34, 'dt de'),
    ('Josh', 'JOS', 'Joshua', 24, 'jos jsh'),
    ('Judg', 'JDG', 'Judges', 21, 'jdg jg jdgs'),
    ('Ruth', 'RUT', 'Ruth', 4, 'rt ru'),
    ('1Sam', '1SA', '1 Samuel', 31, '1sa 1 sm first samuel i samuel'),
    ('2Sam', '2SA', '2 Samuel', 24, '2sa 2 sm second samuel ii samuel'),
    ('1Kgs', '1KI', '1 Kings', 22, '1ki 1 kgs first kings i kings'),
    ('2Kgs', '2KI', '2 Kings', 25, '2ki 2 kgs second kings ii kings'),
    ('1Chr', '1CH', '1 Chronicles', 29, '1ch 1 chron first chronicles i chronicles'),
    ('2Chr', '2CH', '2 Chronicles', 36, '2ch 2 chron second chronicles ii chronicles'),
    ('Ezra', 'EZR', 'Ezra', 10, 'ezr'),
    ('Neh', 'NEH', 'Nehemiah', 13, 'ne'),
    ('Esth', 'EST', 'Esther', 10, 'est es'),
    ('Job', 'JOB', 'Job', 42, 'jb'),
    ('Ps', 'PSA', 'Psalms', 150, 'psalm psa pss ps psm'),
    ('Prov', 'PRO', 'Proverbs', 31, 'pr prv proverb'),
    ('Eccl', 'ECC', 'Ecclesiastes', 12, 'ecc ec qoheleth'),
    ('Song', 'SNG', 'Song of Songs', 8, 'song of solomon sos so canticles ss'),
    ('Isa', 'ISA', 'Isaiah', 66, 'is'),
    ('Jer', 'JER', 'Jeremiah', 52, 'je jr'),
    ('Lam', 'LAM', 'Lamentations', 5, 'la'),
    ('Ezek', 'EZK', 'Ezekiel', 48, 'eze ezk'),
    ('Dan', 'DAN', 'Daniel', 12, 'da dn'),
    ('Hos', 'HOS', 'Hosea', 14, 'ho'),
    ('Joel', 'JOL', 'Joel', 3, 'jl'),
    ('Amos', 'AMO', 'Amos', 9, 'am'),
    ('Obad', 'OBA', 'Obadiah', 1, 'ob'),
    ('Jonah', 'JON', 'Jonah', 4, 'jnh'),
    ('Mic', 'MIC', 'Micah', 7, 'mi'),
    ('Nah', 'NAM', 'Nahum', 3, 'na'),
    ('Hab', 'HAB', 'Habakkuk', 3, 'hb'),
    ('Zeph', 'ZEP', 'Zephaniah', 3, 'zep zp'),
    ('Hag', 'HAG', 'Haggai', 2, 'hg'),
    ('Zech', 'ZEC', 'Zechariah', 14, 'zec zc'),
    ('Mal', 'MAL', 'Malachi', 4, 'ml'),
    ('Matt', 'MAT', 'Matthew', 28, 'mt mat'),
    ('Mark', 'MRK', 'Mark', 16, 'mk mrk mr'),
    ('Luke', 'LUK', 'Luke', 24, 'lk luk'),
    ('John', 'JHN', 'John', 21, 'jn jhn joh'),
    ('Acts', 'ACT', 'Acts', 28, 'ac act'),
    ('Rom', 'ROM', 'Romans', 16, 'ro rm'),
    ('1Cor', '1CO', '1 Corinthians', 16, '1co first corinthians i corinthians'),
    ('2Cor', '2CO', '2 Corinthians', 13, '2co second corinthians ii corinthians'),
    ('Gal', 'GAL', 'Galatians', 6, 'ga'),
    ('Eph', 'EPH', 'Ephesians', 6, 'ephes'),
    ('Phil', 'PHP', 'Philippians', 4, 'php pp'),
    ('Col', 'COL', 'Colossians', 4, 'co'),
    ('1Thess', '1TH', '1 Thessalonians', 5, '1th 1 thes first thessalonians i thessalonians'),
    ('2Thess', '2TH', '2 Thessalonians', 3, '2th 2 thes second thessalonians ii thessalonians'),
    ('1Tim', '1TI', '1 Timothy', 6, '1ti first timothy i timothy'),
    ('2Tim', '2TI', '2 Timothy', 4, '2ti second timothy ii timothy'),
    ('Titus', 'TIT', 'Titus', 3, 'tit ti'),
    ('Phlm', 'PHM', 'Philemon', 1, 'phm philem'),
    ('Heb', 'HEB', 'Hebrews', 13, 'he'),
    ('Jas', 'JAS', 'James', 5, 'jm ja'),
    ('1Pet', '1PE', '1 Peter', 5, '1pe 1 pt first peter i peter'),
    ('2Pet', '2PE', '2 Peter', 3, '2pe 2 pt second peter ii peter'),
    ('1John', '1JN', '1 John', 5, '1jn 1 jn first john i john'),
    ('2John', '2JN', '2 John', 1, '2jn 2 jn second john ii john'),
    ('3John', '3JN', '3 John', 1, '3jn 3 jn third john iii john'),
    ('Jude', 'JUD', 'Jude', 1, 'jud jd'),
    ('Rev', 'REV', 'Revelation', 22, 're rv revelations apocalypse'),
]

ORDER = {b[0]: i + 1 for i, b in enumerate(BOOKS)}
BY_OSIS = {b[0]: b for b in BOOKS}
BY_USFM = {b[1]: b for b in BOOKS}


def _key(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


ALIASES: dict[str, str] = {}
for _osis, _usfm, _name, _n, _extra in BOOKS:
    _names = [_osis, _usfm, _name]
    # Multi-word extras ("first samuel", "1 sm", "song of solomon") are kept whole.
    _names += re.findall(r'(?:first|second|third|iii|ii|i|[123]) [a-z]+|song of solomon', _extra)
    _names += [t for t in _extra.split(' ') if re.match(r'^[a-z0-9]*[a-z]{2,}$', t)
               and t not in ('first', 'second', 'third', 'of')]
    for _a in _names:
        ALIASES.setdefault(_key(_a), _osis)
# Very short aliases collide with ordinary words in a search; keep only those that cannot be read as English.
for _w in ('is', 'am', 'he', 'na', 'do', 'ne', 'so', 'ex', 'la', 'be'):
    ALIASES.pop(_w, None)

REF_RE = re.compile(
    r'^\s*((?:[123]|i{1,3}|first|second|third)?\s*[a-z][a-z .]*?)\s*(\d{1,3})(?:\s*[:.]\s*(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?)?\s*$',
    re.I)


def parse_ref(text: str):
    """'John 3:16', 'ps 23', '1 cor 13:4-7' -> (osis, chapter, first verse or None, last verse or None)."""
    m = REF_RE.match(text)
    if not m:
        return None
    osis = ALIASES.get(_key(m.group(1)))
    if not osis:
        return None
    ch = int(m.group(2))
    if ch < 1 or ch > BY_OSIS[osis][3]:
        return None
    v1 = int(m.group(3)) if m.group(3) else None
    v2 = int(m.group(4)) if m.group(4) else v1
    if v1 and v2 and v2 < v1:
        v1, v2 = v2, v1
    return osis, ch, v1, v2


def name(osis: str) -> str:
    return BY_OSIS[osis][2]


def ref_label(osis: str, ch: int, v1: int | None, v2: int | None = None, c2: int | None = None) -> str:
    n = name(osis)
    if osis == 'Ps':
        n = 'Psalm'
    if v1 is None:
        return f'{n} {ch}'
    if c2 and c2 != ch:
        return f'{n} {ch}:{v1}–{c2}:{v2}'
    if v2 and v2 != v1:
        return f'{n} {ch}:{v1}–{v2}'
    return f'{n} {ch}:{v1}'
