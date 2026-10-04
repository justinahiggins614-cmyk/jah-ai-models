#!/usr/bin/env python3
"""Build archive.html: the unified A-Z archive hub for the Signature AI Phone Book.

Static shell is generated from ai-catalog.json (the canonical AI identity source):
- count header stamped with the REAL current totals (core AIs + Word-AIs)
- core AIs as A-Z collapsible <details> lists; the letter summaries (with per-letter
  counts) are static so crawlers see them; the per-AI rows lazy-load from
  ai-catalog.json only when a letter is opened (never loads all at once)
- search box over the core AIs (lazy-loads the catalog on first use)
- Word-AI leg: A-Z letter tiles linking to the existing word-ai-<letter>.html
  pages (reused, never duplicated)

HOOK (never one-run-behind): build_ai_catalog.py calls build_archive.main() at the
end of its own main(), AFTER ai-catalog.json + api.json are flushed and the hero
is stamped. Re-run after any catalog change:
    python3 code/build_archive.py
"""
import gzip
import html
import io
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BASE = "https://justinahiggins614-cmyk.github.io/jah-ai-models/"
WORDAI_IDX = "https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz"

PAGE_CSS = (
    'body{background:#05080f;color:#e8ecf5;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
    'margin:0;padding:0;line-height:1.5}'
    '.wrap{max-width:980px;margin:0 auto;padding:20px 16px 70px}'
    'a{color:#ffd76a}'
    '.topnav{font-size:.85em;color:#9aa3b8;margin-bottom:14px}'
    'h1{color:#ffd76a;font-size:1.7em;margin:.2em 0}'
    'h2{color:#ffd76a;font-size:1.25em;margin:1.6em 0 .4em;border-bottom:1px solid #2c4a8a;padding-bottom:6px}'
    '.lede{color:#c7cddb;max-width:62em}'
    '.countline{color:#9aa3b8;font-size:.95em;margin:12px 0;padding:10px 14px;border:1px solid #2c4a8a;border-radius:10px;background:#0b1120}'
    '.countline b{color:#ffd76a}'
    '.searchbox{margin:16px 0}'
    '.searchbox input{width:100%;max-width:560px;padding:11px 14px;font-size:1em;border:1px solid #2c4a8a;border-radius:10px;background:#0d1424;color:#e8ecf5}'
    '.letters{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}'
    '.letters a{display:inline-block;min-width:52px;text-align:center;padding:8px 10px;border:1px solid #2c4a8a;border-radius:8px;background:#0d1424;text-decoration:none;font-weight:700}'
    '.letters a small{display:block;font-weight:400;font-size:.72em;color:#9aa3b8}'
    '.azlist{display:grid;gap:8px;margin:14px 0}'
    'details.az{border:1px solid #2c4a8a;border-radius:10px;background:#0b1120;overflow:hidden}'
    'details.az summary{cursor:pointer;padding:12px 14px;list-style:none;display:flex;align-items:center;gap:12px}'
    'details.az summary::-webkit-details-marker{display:none}'
    'details.az summary:hover{background:#101a30}'
    '.azl{font-size:1.4em;font-weight:800;color:#ffd76a;min-width:1.4em;text-align:center}'
    '.azc{color:#9aa3b8;font-size:.9em}'
    '.azbody{padding:4px 14px 16px;border-top:1px dotted #1c2740}'
    '.entries{list-style:none;margin:8px 0 0;padding:0;columns:2;column-gap:24px}'
    '@media(max-width:640px){.entries{columns:1}}'
    '.arow{break-inside:avoid;padding:6px 0;border-bottom:1px dotted #1c2740;font-size:.93em}'
    '.stamp{color:#8b93a7;font-size:.8em;margin-left:8px;font-family:monospace}'
    '.tbadge{font-size:.68em;font-weight:700;margin-left:8px;padding:2px 7px;border-radius:20px;border:1px solid #3a557f;color:#9fc2ff;white-space:nowrap}'
    '.t-system{color:#ffd76a;border-color:#8a6d1f}'
    '.t-persona{color:#ff9d9d;border-color:#7f3a3a}'
    '.fan{font-size:.75em;color:#8b93a7;margin-left:8px;font-style:italic}'
    '.loading,.nores{color:#9aa3b8;font-style:italic}'
    '.resline{color:#9aa3b8;font-size:.9em;margin:10px 0 0}'
    '.fineprint{color:#8b93a7;font-size:.82em;margin-top:26px;border-top:1px solid #1c2740;padding-top:14px}'
)


def esc(s):
    return html.escape(str(s), quote=True)


def letter_of(name):
    c = (name.strip()[:1] or "#").upper()
    return c if c.isalpha() and len(c) == 1 and "A" <= c <= "Z" else "#"


def fetch_wordai_letters():
    """Letter -> count from the live word-AI index (curl: reliable through egress)."""
    r = subprocess.run(
        ["curl", "-sL", "--max-time", "90", "-A", "JAH-archive-build/1.0", WORDAI_IDX],
        capture_output=True, timeout=100)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("curl fetch failed for word-AI index")
    rows = json.loads(gzip.decompress(r.stdout).decode("utf-8"))
    groups = {}
    for w, _n in rows:
        groups[letter_of(w)] = groups.get(letter_of(w), 0) + 1
    return groups, len(rows)


def build():
    catalog = json.load(io.open(os.path.join(REPO, "ai-catalog.json"), encoding="utf-8"))
    counts = catalog["counts"]
    records = catalog["records"]
    emb, sys_n, per_n, dom_n = (counts["embedded_total"], counts["system"],
                               counts["persona"], counts["domain"])
    wa_total = counts["wordai_index_records"]
    asof = counts["wordai_as_of"]
    pub = counts["published_total"]

    core_groups = {}
    for r in records:
        core_groups.setdefault(letter_of(r["NAME"]), []).append(r["NAME"])
    letters = sorted(core_groups.keys())

    try:
        wa_letters, wa_live = fetch_wordai_letters()
    except Exception as e:  # noqa: BLE001 - keep last good numbers, say so loudly
        print("word-AI index unreachable (%s); deriving tiles from existing hub" % e)
        hub = io.open(os.path.join(REPO, "word-ai.html"), encoding="utf-8").read()
        wa_letters = {}
        for slug, label, n in re.findall(
                r'<a href="word-ai-([0-9a-z])\.html">([^<]+)<small>([\d,]+) AIs</small></a>', hub):
            L = "#" if slug == "0" else label.strip().upper()[:1]
            wa_letters[L] = int(n.replace(",", ""))
        wa_live = sum(wa_letters.values())

    fmt = lambda n: format(n, ",d")  # noqa: E731

    # --- core-AI letter details (static summaries; rows lazy-load via JS) ---
    det = []
    for L in letters:
        n = len(core_groups[L])
        label = "0-9 &amp; symbols" if L == "#" else L
        det.append(
            '<details class="az" data-letter="%s"><summary>'
            '<span class="azl">%s</span><span class="azc">%s core AIs</span>'
            '</summary><div class="azbody"><p class="loading">Open to load this letter\u2019s AIs.</p></div>'
            '</details>' % (L, label, fmt(n)))
    az_html = '<div class="azlist">%s</div>' % "".join(det)

    # --- word-AI letter tiles (reuse existing pages; never duplicate) ---
    tiles = []
    for L in sorted(wa_letters.keys()):
        slug = "0" if L == "#" else L.lower()
        label = "0\u20139 &amp; symbols" if L == "#" else L
        tiles.append('<a href="word-ai-%s.html">%s<small>%s AIs</small></a>'
                     % (slug, label, fmt(wa_letters[L])))
    tile_html = '<div class="letters">%s</div>' % "".join(tiles)

    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "The Complete AI Archive — The Signature AI Phone Book",
        "description": "Every AI file in the phone book, A to Z: %d core AIs and %d Word-AIs." % (emb, wa_total),
        "url": BASE + "archive.html",
        "isPartOf": {"@type": "WebSite", "name": "The Signature AI Phone Book", "url": BASE},
    }

    js = r"""
<script>
(function(){
  var CAT=null,CATP=null;
  function loadCat(cb){
    if(CAT) return cb(CAT);
    if(!CATP){CATP=fetch('ai-catalog.json').then(function(r){return r.json();})
      .then(function(j){CAT=j;return j;}).catch(function(){return null;});}
    CATP.then(cb);
  }
  function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function letterOf(n){var c=(n.trim().charAt(0)||'#').toUpperCase();return /[A-Z]/.test(c)?c:'#';}
  function rowHtml(r){
    var slug=String((r.ARTIFACTS&&r.ARTIFACTS.deep_link)||'').replace(/^#file-/,'');
    var h='<li class="arow"><a href="index.html?dial='+encodeURIComponent(slug)+'">'+esc(r.NAME)+'</a>';
    h+='<span class="tbadge t-'+r.TYPE+'">'+esc(r.TYPE.toUpperCase())+'</span>';
    h+='<span class="stamp">'+esc(r.ID)+'</span>';
    if(r.TYPE==='persona')h+='<span class="fan">fan-style interpretation \u00b7 not affiliated</span>';
    h+='</li>';return h;
  }
  function byName(a,b){var x=a.NAME.toLowerCase(),y=b.NAME.toLowerCase();return x<y?-1:x>y?1:0;}
  function renderLetter(det){
    var L=det.getAttribute('data-letter'),body=det.querySelector('.azbody');
    if(body.getAttribute('data-loaded'))return;
    body.setAttribute('data-loaded','1');
    body.innerHTML='<p class="loading">Loading this letter\u2019s AIs\u2026</p>';
    loadCat(function(j){
      if(!j){body.innerHTML='<p class="loading">Could not load the catalog \u2014 <a href="index.html#thebook">open the phone book</a> instead.</p>';return;}
      var rows=j.records.filter(function(r){return letterOf(r.NAME)===L;}).sort(byName);
      body.innerHTML='<ul class="entries">'+rows.map(rowHtml).join('')+'</ul>';
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll('details.az'),function(det){
    det.addEventListener('toggle',function(){if(det.open)renderLetter(det);});
  });
  var si=document.getElementById('asearch'),sr=document.getElementById('asearchres'),t=null;
  si.addEventListener('input',function(){clearTimeout(t);t=setTimeout(doSearch,250);});
  function doSearch(){
    var q=si.value.trim().toLowerCase();
    if(q.length<2){sr.innerHTML='';return;}
    loadCat(function(j){
      if(!j)return;
      var hits=j.records.filter(function(r){
        return r.NAME.toLowerCase().indexOf(q)>-1||r.ID.toLowerCase().indexOf(q)>-1||String(r.CATEGORY||'').toLowerCase().indexOf(q)>-1;
      }).sort(byName).slice(0,40);
      if(!hits.length){sr.innerHTML='<p class="nores">No core AI matches \u201c'+esc(si.value)+'\u201d. Try the <a href="word-ai.html">Word-AI directory</a> or the <a href="index.html#thebook">phone book</a>.</p>';return;}
      sr.innerHTML='<p class="resline">'+hits.length+' match'+(hits.length===1?'':'es')+' in the core archive:</p><ul class="entries">'+hits.map(rowHtml).join('')+'</ul>';
    });
  }
})();
</script>
"""

    body = (
        '<div class="topnav"><a href="index.html">\u260e The Signature AI Phone Book</a> &rsaquo; Archive</div>'
        '<h1>\U0001F4DA The Complete AI Archive</h1>'
        '<p class="lede">Every AI in the phone book, all in one place. The core archive \u2014 '
        'Signature system AIs, the persona archive, and a domain AI for every need in life \u2014 '
        'plus a Word-AI for every word. Tap a letter, tap an AI, and its full file opens: '
        'dossier, working demo, dialog, read-aloud, copy, download.</p>'
        '<p class="countline"><b id="archTotal">%s</b> AI files on record: '
        '<b>%d</b> core AIs (%d system &middot; %d persona &middot; %d domain) + '
        '<b>%s</b> Word-AIs &middot; Last synchronized %s</p>'
        '<div class="searchbox"><input type="text" id="asearch" '
        'placeholder="Search the core archive\u2026 name, ID, or subject" '
        'aria-label="Search the archive" autocomplete="off"></div>'
        '<div id="asearchres"></div>'
        '<h2>\U0001F4D6 Core AIs \u2014 A to Z</h2>'
        '<p class="lede">Signature system minds, persona simulations, and domain specialists. '
        'Tap a letter to load its AIs; each row links straight to the AI\u2019s file.</p>'
        '%s'
        '<h2>\U0001F520 Word-AIs \u2014 one AI per word</h2>'
        '<p class="lede">%s word AIs, each dialable, talkable, readable aloud, and downloadable. '
        'Tap a letter to open its directory page.</p>'
        '%s'
        '<p class="fineprint">Persona AIs marked as fan-style interpretations are independent '
        'simulations, not affiliated with or endorsed by any rights holder. Every AI carries a '
        'permanent Signature stamp ID and its own 11-digit Signature phone number.</p>'
        % (fmt(pub), emb, sys_n, per_n, dom_n, fmt(wa_total), esc(asof),
           az_html, fmt(wa_live), tile_html)
    )

    page = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>AI Archive A\u2013Z \u2014 The Signature AI Phone Book</title>\n'
        '<meta name="description" content="The complete A\u2013Z archive of the Signature AI Phone Book: '
        '%d core AIs and %d Word-AIs, every file dialable, searchable, and downloadable.">\n'
        '<link rel="canonical" href="%sarchive.html">\n'
        '<script type="application/ld+json">\n%s\n</script>\n'
        '<style>%s</style>\n</head>\n<body>\n<div class="wrap">\n%s\n</div>\n%s\n</body>\n</html>\n'
        % (emb, wa_total, BASE, json.dumps(ld, ensure_ascii=False), PAGE_CSS, body, js)
    )
    out = os.path.join(REPO, "archive.html")
    io.open(out, "w", encoding="utf-8").write(page)
    print("archive.html written: %s total (%d core + %s word-AIs), %d core letters, %d word-AI letters"
          % (fmt(pub), emb, fmt(wa_total), len(letters), len(wa_letters)))
    return pub, emb, wa_total


def main():
    build()


if __name__ == "__main__":
    main()
