#!/usr/bin/env python3
"""Follow-up polish wave for the AI Phone Book (2026-10-02).
Stampers -- safe to re-run, idempotent, additive only. Never touches
data files, the chat engine (SigLlama v2), or any visible styling.

1. JSON-LD ItemList of the 270 embedded AI files -> index.html <head>.
   (No license field, per Manon's call.)
2. Static word-AI directory: word-ai.html hub + word-ai-<letter>.html pages,
   each entry linking index.html?dial=JAH-AI-WORD-###### .
3. sitemap.xml gains the new directory pages.
"""
import gzip
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://justinahiggins614-cmyk.github.io/jah-ai-models/'
WORDAI_IDX = 'https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz'


def esc(s):
    return html.escape(str(s), quote=True)


# ---------- 1. JSON-LD ItemList ----------
def build_itemlist():
    cat = json.load(open(os.path.join(ROOT, 'ai-catalog.json'), encoding='utf-8'))
    items = []
    for i, r in enumerate(cat['records'], 1):
        art = r.get('ARTIFACTS', {})
        items.append({
            '@type': 'ListItem',
            'position': i,
            'item': {
                '@type': 'SoftwareApplication',
                'name': r.get('NAME', ''),
                'identifier': r.get('ID', ''),
                'description': str(r.get('DESCRIPTION', ''))[:300],
                'url': art.get('live_url', BASE),
                'applicationCategory': 'AI persona / assistant',
                'operatingSystem': 'Any',
                'creator': {'@type': 'Person', 'name': 'Justin Addam Higgins'},
                'isPartOf': {'@type': 'WebSite', 'name': 'The Signature AI Phone Book', 'url': BASE},
            },
        })
    ld = {
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        'name': 'The Signature AI Phone Book — AI directory',
        'description': 'Every published AI file in the archive: Signature system AIs, persona archive, and domain AIs for every need in life.',
        'numberOfItems': len(items),
        'itemListElement': items,
    }
    return ld, len(items)


# ---------- 2. word-AI directory ----------
PAGE_CSS = (
    'body{background:#05080f;color:#e8ecf5;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
    'margin:0;padding:0;line-height:1.5}'
    '.wrap{max-width:900px;margin:0 auto;padding:20px 16px 60px}'
    'a{color:#ffd76a}.topnav{font-size:.85em;color:#9aa3b8;margin-bottom:14px}'
    'h1{color:#ffd76a;font-size:1.5em;margin:.2em 0}'
    '.lede{color:#c7cddb;max-width:60em}'
    '.letters{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}'
    '.letters a{display:inline-block;min-width:44px;text-align:center;padding:8px 10px;border:1px solid #2c4a8a;'
    'border-radius:8px;background:#0d1424;text-decoration:none;font-weight:700}'
    '.letters a small{display:block;font-weight:400;font-size:.72em;color:#9aa3b8}'
    '.entries{list-style:none;margin:0;padding:0;columns:2;column-gap:24px}'
    '@media(max-width:600px){.entries{columns:1}}'
    '.entries li{break-inside:avoid;padding:5px 0;border-bottom:1px dotted #1c2740;font-size:.92em}'
    '.entries .stamp{color:#8b93a7;font-size:.8em;margin-left:8px;font-family:monospace}'
    '.countline{color:#9aa3b8;font-size:.9em;margin:10px 0}'
)

PAGE_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — The Signature AI Phone Book</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<style>{css}</style>
</head>
<body>
<div class="wrap">
<div class="topnav"><a href="index.html">☎ The Signature AI Phone Book</a> &rsaquo; <a href="word-ai.html">Word-AI Directory</a></div>
{body}
</div>
</body>
</html>
"""


def word_display(w):
    w = w.strip()
    return (w[:1].upper() + w[1:] if w else w) + ' AI'


def fetch_wordai_index():
    import urllib.request
    req = urllib.request.Request(WORDAI_IDX, headers={'User-Agent': 'JAH-polish/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    return json.loads(gzip.decompress(raw).decode('utf-8'))


def build_wordai_pages():
    rows = fetch_wordai_index()
    groups = {}
    for w, n in rows:
        L = (w.strip()[:1] or '#').upper()
        if not L.isalpha():
            L = '#'
        groups.setdefault(L, []).append((w, n))
    letters = sorted(groups.keys())
    # hub
    cards = []
    for L in letters:
        label = '0–9 &amp; symbols' if L == '#' else L
        cards.append('<a href="word-ai-%s.html">%s<small>%d AIs</small></a>'
                     % ('0' if L == '#' else L.lower(), label, len(groups[L])))
    hub_body = (
        '<h1>📖 Word-AI Directory</h1>'
        '<p class="lede">Every word with its own Signature AI — each one dialable, talkable, '
        'readable aloud, and downloadable. Tap a letter, tap a word AI, and its file opens '
        'on the phone book. New word AIs arrive with the dictionary drip.</p>'
        '<p class="countline"><b>%d</b> word AIs on record.</p>'
        '<div class="letters">%s</div>'
        '<p class="lede">Word AIs are Signature-made assistants for individual words — '
        'definition, usage, sentences, and a working chat, each stamped with a permanent '
        'JAH-AI-WORD-###### ID.</p>' % (len(rows), ''.join(cards))
    )
    pages = {'word-ai.html': PAGE_SHELL.format(
        title='Word-AI Directory', desc='Browse every word AI in the Signature AI Phone Book, A to Z.',
        canon=BASE + 'word-ai.html', css=PAGE_CSS, body=hub_body)}
    for L in letters:
        slug = '0' if L == '#' else L.lower()
        ents = sorted(groups[L], key=lambda t: t[0].lower())
        lis = []
        for w, n in ents:
            stamp = 'JAH-AI-WORD-%06d' % n
            lis.append('<li><a href="index.html?dial=%s">%s</a><span class="stamp">%s</span></li>'
                       % (stamp, esc(word_display(w)), stamp))
        label = '0–9 & symbols' if L == '#' else '“' + L + '”'
        body = ('<h1>Word AIs — %s</h1>'
                '<p class="countline"><b>%d</b> word AIs.</p>'
                '<ul class="entries">%s</ul>' % (label, len(ents), ''.join(lis)))
        pages['word-ai-%s.html' % slug] = PAGE_SHELL.format(
            title='Word AIs — ' + ('0-9' if L == '#' else L),
            desc='Word AIs starting with %s in the Signature AI Phone Book.' % label,
            canon=BASE + 'word-ai-%s.html' % slug, css=PAGE_CSS, body=body)
    for name, content in pages.items():
        open(os.path.join(ROOT, name), 'w', encoding='utf-8').write(content)
    return sorted(pages.keys()), len(rows)


# ---------- 3. sitemap ----------
def stamp_sitemap(page_names):
    p = os.path.join(ROOT, 'sitemap.xml')
    s = open(p, encoding='utf-8').read()
    s = re.sub(r'  <!-- wordai-dir -->.*?\n', '', s)
    entries = ''.join(
        '  <url><loc>%s%s</loc><changefreq>weekly</changefreq></url>  <!-- wordai-dir -->\n' % (BASE, n)
        for n in page_names)
    s = s.replace('</urlset>', entries + '</urlset>', 1)
    open(p, 'w', encoding='utf-8').write(s)


def main():
    ld, count = build_itemlist()
    # stamp (separated so the count prints honestly)
    p = os.path.join(ROOT, 'index.html')
    s = open(p, encoding='utf-8').read()
    block = ('<!-- JAH-ITEMLIST-START -->\n'
             '<script type="application/ld+json" id="jah-ld-itemlist">\n'
             + json.dumps(ld, ensure_ascii=False, separators=(',', ':'))
             + '\n</script>\n<!-- JAH-ITEMLIST-END -->')
    s = re.sub(r'<!-- JAH-ITEMLIST-START -->.*?<!-- JAH-ITEMLIST-END -->\n?', '', s, flags=re.S)
    s = s.replace('</head>', block + '\n</head>', 1)
    open(p, 'w', encoding='utf-8').write(s)
    print('ItemList stamped: %d AI files' % count)

    pages, n_words = build_wordai_pages()
    print('word-AI directory: %d pages, %d word AIs' % (len(pages), n_words))
    stamp_sitemap(pages)
    print('sitemap updated')


if __name__ == '__main__':
    main()
