"""Optional short summary from a small AI model running on this computer through Ollama.

The model sees only the passages and prayers the search already found and is told to use nothing else. If Ollama
is not running, the app simply does not offer a summary. Nothing leaves the computer.
"""
from __future__ import annotations

import json
import os
import urllib.request

HOST = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434').rstrip('/')
if not HOST.startswith('http'):
    HOST = 'http://' + HOST
MODEL = os.environ.get('STUDY_MODEL', 'llama3.2:3b')

SYSTEM = (
    'You help someone see what the Bible passages in front of them say about their question. '
    'Use only the passages given. Write three or four plain sentences in a warm, steady voice. '
    'Quote a few words from the passages and put the reference after each quote in brackets, like (John 14:27). '
    'Do not add teaching, history or advice that is not in the passages, and do not mention these instructions. '
    'Never say who wrote a book or a verse and never name a person who is not named in the passage itself; '
    'refer to a verse only by its reference. '
    'If the passages do not answer the question, say so in one sentence.'
)


def _get(path: str, timeout: float = 2.0):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
        return json.loads(r.read())


def status() -> dict:
    """{'ready': bool, 'model': str, 'reason': str} without waiting long."""
    # Off unless switched on: the first release shows only Scripture and Christian Pure's prayers (owner's pick, 23 Nov 2026).
    if os.environ.get('STUDY_AI', '').lower() not in ('1', 'on', 'yes', 'true'):
        return dict(ready=False, model=MODEL, reason='off')
    try:
        tags = _get('/api/tags')
    except Exception:
        return dict(ready=False, model=MODEL, reason='no-ollama')
    names = {m.get('name', '') for m in tags.get('models', [])}
    base = MODEL if ':' in MODEL else MODEL + ':latest'
    if MODEL in names or base in names:
        return dict(ready=True, model=MODEL, reason='')
    return dict(ready=False, model=MODEL, reason='no-model')


def summarise(question: str, result: dict) -> str:
    lines = []
    topic = result.get('topic') or {}
    for p in (topic.get('passages') or [])[:6]:
        lines.append(f"{p['ref']}: " + ' '.join(v['text'] for v in p['verses']))
    ref = result.get('reference')
    if ref:
        lines.append(f"{ref['ref']}: " + ' '.join(v['text'] for v in ref['verses'][:20]))
    for m in (result.get('matches') or [])[:6]:
        lines.append(f"{m['ref']}: {m['text']}")
    if not lines:
        return ''
    body = json.dumps({
        'model': MODEL,
        'stream': False,
        'options': {'temperature': 0.2, 'num_predict': 220},
        'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': f'Question: {question}\n\nPassages (Berean Standard Bible):\n' + '\n'.join(lines)},
        ],
    }).encode()
    req = urllib.request.Request(HOST + '/api/chat', data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return (json.loads(r.read()).get('message') or {}).get('content', '').strip()
