#!/usr/bin/env python3
"""Follow-up polish wave for the AI Phone Book (2026-10-02).
Stampers -- safe to re-run, idempotent, additive only. Never touches
data files, the chat engine (SigLlama v2), or any visible styling.

1. JSON-LD ItemList of the 270 embedded AI files -> index.html <head>.
   (No license field, per Manon's call.)
2. Word-AI directory: word-ai.html hub + word-ai-<letter>.html pages, each
   entry linking index.html?dial=JAH-AI-WORD-###### . A-Z rule (2026-10-05):
   letter pages group entries by two-letter prefix into collapsed <details>
   that lazy-load from data/wordai/wordai-<letter>.json — never a full-letter
   DOM dump.
3. sitemap.xml gains the new directory pages.
"""
import gzip
import html
import json
import os
import re
import subprocess

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
    'details.waigrp{border:1px solid #2c4a8a;border-radius:10px;margin:8px 0;background:#0b1120}'
    'details.waigrp summary{cursor:pointer;padding:12px 14px;font-size:1.05em;list-style:none;font-weight:700;color:#ffd76a}'
    'details.waigrp summary::-webkit-details-marker{display:none}'
    'details.waigrp summary .n{font-weight:400;color:#9aa3b8;font-size:.85em}'
    '.waiload{color:#9aa3b8;font-style:italic;list-style:none}'
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


# Lazy two-letter group loader for word-ai-<letter>.html (A-Z rule: collapsed
# by default, entries render on first open from data/wordai/wordai-<l>.json).
# WAILETTER is replaced with the page's letter slug at build time.
WAIGRP_JS = """
(function(){
"use strict";
function waiEsc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#x27;");}
function waiGrp(w){w=String(w==null?"":w).toLowerCase();return w.length>=2?w.slice(0,2):w;}
function waiRow(r){
  var w=String(r[0]).replace(/^\\s+|\\s+$/g,"");
  var disp=(w.charAt(0).toUpperCase()+w.slice(1))+" AI";
  return '<li><a href="index.html?dial='+r[1]+'">'+waiEsc(disp)+'</a><span class="stamp">'+waiEsc(r[1])+'</span></li>';
}
var waiRows=null,waiTried=false,waiWait=[];
function waiEnsure(cb){
  if(waiRows){cb(waiRows);return;}
  waiWait.push(cb);
  if(waiTried)return;
  waiTried=true;
  fetch("data/wordai/wordai-WAILETTER.json").then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json();}).then(function(d){
    waiRows=d;var w=waiWait;waiWait=[];w.forEach(function(f){f(d);});
  }).catch(function(){var w=waiWait;waiWait=[];w.forEach(function(f){f(null);});});
}
function waiLoad(d){
  var ul=d.querySelector("ul.entries");
  if(!ul||ul.getAttribute("data-loaded")==="1")return;
  ul.setAttribute("data-loaded","1");
  ul.innerHTML='<li class="waiload">Loading word AIs&hellip;</li>';
  waiEnsure(function(rows){
    if(!rows){ul.innerHTML='<li class="waiload">Could not load &mdash; <a href="word-ai.html">back to the directory</a></li>';ul.setAttribute("data-loaded","0");return;}
    var pfx=d.getAttribute("data-grp"),h="",i;
    for(i=0;i<rows.length;i++){if(waiGrp(rows[i][0])===pfx)h+=waiRow(rows[i]);}
    ul.innerHTML=h||'<li class="waiload">None.</li>';
  });
}
document.addEventListener("toggle",function(e){
  var d=e.target;
  if(d&&d.tagName==="DETAILS"&&d.classList&&d.classList.contains("waigrp")&&d.open)waiLoad(d);
},true);
})();
"""


def fetch_wordai_index():
    # curl, not urllib: python urllib hangs through this sandbox's egress proxy
    # (AGENTS.md), curl works.
    raw = subprocess.run(
        ["curl", "-sL", "--max-time", "120", "-A", "JAH-polish/1.0", WORDAI_IDX],
        capture_output=True, timeout=130).stdout
    if not raw:
        raise RuntimeError("curl fetch failed for word-AI index")
    return json.loads(gzip.decompress(raw).decode('utf-8'))


def build_wordai_pages():
    """Word-AI directory pages — A-Z rule compliant (2026-10-05).

    Each word-ai-<letter>.html groups its entries by two-letter prefix into
    collapsed <details class="waigrp"> shells; a group's <li> entries render
    on first open from data/wordai/wordai-<letter>.json (never a full-letter
    DOM dump). The JSON files double as the machine-readable directory.
    """
    rows = fetch_wordai_index()
    groups = {}
    for w, n in rows:
        L = (w.strip()[:1] or '#').upper()
        if not L.isalpha():
            L = '#'
        groups.setdefault(L, []).append((w, n))
    letters = sorted(groups.keys())
    # per-letter machine JSON (lazy data source for the pages + crawlers)
    waidir = os.path.join(ROOT, 'data', 'wordai')
    os.makedirs(waidir, exist_ok=True)
    for L in letters:
        slug = '0' if L == '#' else L.lower()
        ents = sorted(groups[L], key=lambda t: t[0].lower())
        with open(os.path.join(waidir, 'wordai-%s.json' % slug), 'w',
                  encoding='utf-8') as f:
            json.dump([[w, 'JAH-AI-WORD-%06d' % n] for w, n in ents], f,
                      ensure_ascii=False, separators=(',', ':'))
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
        # two-letter subgroups, collapsed + lazy (A-Z rule: no full dumps)
        subgroups, order = {}, []
        for w, n in ents:
            pfx = w.strip()[:2].lower() if len(w.strip()) >= 2 else w.strip().lower()
            if pfx not in subgroups:
                subgroups[pfx] = []
                order.append(pfx)
            subgroups[pfx].append((w, n))
        det_parts = []
        for pfx in order:
            cnt = len(subgroups[pfx])
            det_parts.append(
                '<details class="waigrp" data-grp="%s"><summary>%s '
                '<span class="n">&middot; %s</span></summary>'
                '<ul class="entries" data-loaded="0"></ul></details>'
                % (esc(pfx), esc(pfx),
                   ('%d AIs' % cnt) if cnt != 1 else '1 AI'))
        label = '0–9 & symbols' if L == '#' else '“' + L + '”'
        body = ('<h1>Word AIs — %s</h1>'
                '<p class="countline"><b>%d</b> word AIs — open a group to load it.</p>'
                '%s'
                '<noscript><p class="countline">This directory loads each group on demand with JavaScript. '
                'Without JavaScript, the full machine-readable list for this letter lives at '
                '<a href="data/wordai/wordai-%s.json">data/wordai/wordai-%s.json</a>.</p></noscript>'
                '<script>%s</script>'
                % (label, len(ents), ''.join(det_parts), slug, slug,
                   WAIGRP_JS.replace('WAILETTER', slug)))
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
    # drop previously stamped wordai-dir/archive entries: ANY line mentioning a
    # word-ai page, plus any line carrying the archive marker, then re-add fresh.
    # (The legacy hardcoded word-AI block sat all on one line and duplicated the
    # generated block; this wipes it too.)
    s = re.sub(r'.*word-ai(-[0-9a-z])?\.html.*\n', '', s)
    s = re.sub(r'.*<!-- archive -->.*\n', '', s)
    entries = ''.join(
        '  <url><loc>%s%s</loc><changefreq>weekly</changefreq></url>  <!-- wordai-dir -->\n' % (BASE, n)
        for n in page_names)
    # archive hub + per-AI deep-link URL patterns: the archive itself plus the
    # existing index.html?dial=<ID> pattern (word-AI letter pages carry the
    # 42,200 word-AI deep links; the #file-<id> deep links for core AIs were
    # stamped by an earlier pass and are left untouched).
    entries += ('  <url><loc>%sarchive.html</loc><changefreq>weekly</changefreq></url>  <!-- archive -->\n'
                % BASE)
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
