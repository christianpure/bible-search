/* Christian Pure Bible Search: one page, driven by the address after # so Back and Forward work. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const look = new URLSearchParams(location.search).get('look');
  if (look && /^[abc]$/.test(look)) document.documentElement.dataset.look = look;

  let state = { q: '', result: null, prayerIndex: 0, ai: false };

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function show(id) {
    for (const s of ['start', 'results', 'reader', 'empty']) $(s).hidden = s !== id;
  }

  function readParams() {
    return new URLSearchParams(location.hash.replace(/^#/, ''));
  }

  function chapterHref(osis, ch, from) {
    const p = new URLSearchParams({ read: `${osis}.${ch}` });
    if (from) p.set('from', from);
    return '#' + p.toString();
  }

  function passageNode(p, cls, from) {
    const art = el('article', 'passage' + (cls ? ' ' + cls : ''));
    const text = el('p', 'passage-text');
    p.verses.forEach((v, i) => {
      if (i) text.append(' ');
      if (p.verses.length > 1) text.append(el('sup', 'vnum', String(v.v)));
      text.append(v.text);
    });
    if (p.more > 0) text.append(' …');
    art.append(text);
    const foot = el('p', 'passage-foot');
    foot.append(el('cite', 'ref', p.ref));
    const a = el('a', 'passage-read', 'Read the whole chapter');
    a.href = chapterHref(p.osis, p.chapter, from);
    foot.append(a);
    art.append(foot);
    return art;
  }

  function renderPrayer() {
    const list = (state.result && state.result.prayers) || [];
    $('prayer').hidden = !list.length;
    if (!list.length) return;
    const p = list[state.prayerIndex % list.length];
    $('prayer-title').textContent = p.title;
    $('prayer-text').textContent = p.text;
    const src = $('prayer-source');
    src.textContent = '';
    if (p.url) {
      src.append('From ');
      const a = el('a', null, p.source || 'Christian Pure');
      a.href = p.url; a.target = '_blank'; a.rel = 'noopener';
      src.append(a);
    }
    $('next-prayer').hidden = list.length < 2;
  }

  function render(r) {
    state.result = r; state.prayerIndex = 0;
    const lead = $('lead'), box = $('passages'), rel = $('related');
    lead.textContent = ''; box.textContent = ''; rel.textContent = '';
    $('summary-out').hidden = true;
    $('results').classList.toggle('wants-prayer', r.wants === 'prayer');

    let passages = [];
    if (r.reference) {
      $('kicker').hidden = true;
      $('subject').textContent = r.reference.ref;
      passages = [r.reference];
    } else if (r.topic) {
      $('kicker').hidden = false;
      $('kicker').textContent = 'What the Bible says about';
      $('subject').textContent = r.topic.name;
      passages = r.topic.passages;
    } else if (r.matches.length) {
      $('kicker').hidden = false;
      $('kicker').textContent = 'Verses that use the words';
      $('subject').textContent = r.query.replace(/^"|"$/g, '');
      passages = r.matches.map((m) => ({ ref: m.ref, osis: m.osis, chapter: m.chapter, more: 0, verses: [{ v: 0, text: m.text }] }));
    }

    if (!passages.length && !r.prayers.length && !r.pages.length) {
      $('empty').textContent = `Nothing here matches “${r.query}” yet. Try one word for the subject, such as fear, marriage or hope, or a verse such as John 14:27.`;
      show('empty');
      return;
    }

    passages.forEach((p, i) => (i === 0 ? lead : box).append(passageNode(p, i === 0 ? 'passage--lead' : '', r.query)));
    for (const name of r.related || []) {
      const li = el('li'); const a = el('a', 'chip', name);
      a.href = '#' + new URLSearchParams({ q: name }).toString();
      li.append(a); rel.append(li);
    }
    rel.hidden = !rel.children.length;

    renderPrayer();

    const list = $('page-list'); list.textContent = '';
    const pages = (r.topic && r.topic.page ? [{ title: `Bible verses about ${r.topic.name}`, url: r.topic.page }] : [])
      .concat(r.pages.filter((p) => !(r.topic && r.topic.page && p.url.split('?')[0] === r.topic.page.split('?')[0])));
    for (const p of pages.slice(0, 5)) {
      const li = el('li'); const a = el('a', null, p.title);
      a.href = p.url; a.target = '_blank'; a.rel = 'noopener';
      li.append(a); list.append(li);
    }
    $('pages').hidden = !list.children.length;
    $('summary').hidden = !(state.ai && passages.length);
    show('results');
  }

  async function runSearch(q) {
    state.q = q;
    $('q').value = q;
    document.title = `${q} · Christian Pure Bible Search`;
    const res = await fetch('/api/search?' + new URLSearchParams({ q }));
    render(await res.json());
    $('main').focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  async function runReader(spec, from) {
    const m = /^([1-3]?[A-Za-z]+)\.(\d+)$/.exec(spec || '');
    if (!m) return go('');
    const res = await fetch('/api/chapter?' + new URLSearchParams({ book: m[1], ch: m[2] }));
    if (!res.ok) return go('');
    const p = await res.json();
    $('reader-title').textContent = p.ref;
    document.title = `${p.ref} · Christian Pure Bible Search`;
    const box = $('chapter'); box.textContent = '';
    const text = el('p', 'chapter-text');
    p.verses.forEach((v, i) => { if (i) text.append(' '); text.append(el('sup', 'vnum', String(v.v)), v.text); });
    box.append(text);
    const back = $('back');
    back.textContent = from ? `Back to ${from}` : 'Start again';
    back.href = from ? '#' + new URLSearchParams({ q: from }).toString() : '#';
    const ch = Number(m[2]);
    $('prev').hidden = ch <= 1; $('prev').href = chapterHref(m[1], ch - 1, from);
    $('next').hidden = ch >= p.chapters; $('next').href = chapterHref(m[1], ch + 1, from);
    show('reader');
    window.scrollTo(0, 0);
  }

  function go(q) { location.hash = q ? new URLSearchParams({ q }).toString() : ''; }

  function route() {
    const p = readParams();
    if (p.get('read')) return runReader(p.get('read'), p.get('from'));
    const q = (p.get('q') || '').trim();
    if (q) return runSearch(q);
    $('q').value = '';
    document.title = 'Christian Pure Bible Search';
    show('start');
  }

  async function summarise() {
    const btn = $('summarise'), out = $('summary-out'), again = $('again');
    btn.disabled = true; again.disabled = true;
    btn.textContent = 'Reading the verses…';
    try {
      const res = await fetch('/api/summary', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: state.q }) });
      const d = await res.json();
      $('summary-text').textContent = d.text || d.error || 'The model gave no answer. Write it again, or read the verses above.';
      out.hidden = false;
    } catch (e) {
      $('summary-text').textContent = 'The AI model on this computer did not answer. Check that Ollama is running, then write it again.';
      out.hidden = false;
    }
    btn.disabled = false; again.disabled = false;
    btn.textContent = 'Summarise these verses';
  }

  $('ask').addEventListener('submit', (e) => { e.preventDefault(); const q = $('q').value.trim(); if (q) go(q); });
  $('next-prayer').addEventListener('click', () => { state.prayerIndex += 1; renderPrayer(); });
  $('summarise').addEventListener('click', summarise);
  $('again').addEventListener('click', summarise);
  window.addEventListener('hashchange', route);

  fetch('/api/status').then((r) => r.json()).then((s) => {
    state.ai = !!(s.ai && s.ai.ready);
    if (state.result) $('summary').hidden = !state.ai;
    const site = $('foot-site');
    site.href = `https://christianpure.com/?utm_source=${encodeURIComponent(s.source)}&utm_medium=app&utm_campaign=bible-search-app`;
  }).catch(() => {});
  route();
})();
