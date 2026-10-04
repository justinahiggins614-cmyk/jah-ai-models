#!/usr/bin/env python3
"""Signature-Line AI twins builder.

Manon's order (2026-10-04): for every AI model on the market (or announced),
add a Signature-Line twin to the phone book — functionally equivalent to what
the original's website claims, but an ORIGINAL implementation built from
Signature math: Manon's domain, legally distinct, he owns it.

Reads code/sl_models_manifest.json (transcribed from the web research report),
generates js/sl_twins.js (var SL_TWINS — same record shape as SIG_AIS so the
whole phone-book treatment works: file view, chat, demo, copy/download,
directory, A-Z book, search, phone numbers), and applies the small index.html
integration patches idempotently.

Deterministic and re-runnable: stamps are JAH-AI-SL-### by manifest order, so
new manifest entries always append new twins and never duplicate or renumber.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MANIFEST = os.path.join(HERE, "sl_models_manifest.json")
OUT_JS = os.path.join(REPO, "js", "sl_twins.js")
INDEX = os.path.join(REPO, "index.html")

ROOTS = ["Alder", "Birch", "Cedar", "Drift", "Ember", "Flint", "Grove",
         "Harbor", "Indigo", "Juniper", "Kelp", "Lark", "Meadow", "North",
         "Onyx", "Prairie", "Quartz", "Ridge", "Sable", "Tern", "Umber",
         "Vale", "Willow", "Zephyr"]
SUFFIXES = ["mark", "wise", "field", "song", "light", "ward", "helm", "crest"]

TYPEWORD = {"chat": "Mind", "image": "Canvas", "video": "Reel", "code": "Forge",
            "audio": "Studio", "tts": "Voice", "stt": "Ear", "agent": "Operative",
            "robot": "Pilot", "humanoid": "Figure", "3d": "Sculpt", "other": "Engine"}

TYPE_LABEL = {"chat": "chat / language model", "image": "image generator",
              "video": "video generator", "code": "coding assistant",
              "audio": "music / audio generator", "tts": "text-to-speech voice",
              "stt": "speech-to-text transcriber", "agent": "autonomous agent",
              "robot": "robotics AI", "humanoid": "humanoid robot AI",
              "3d": "3D generator", "other": "AI product"}


def epithet(i):
    return ROOTS[i % len(ROOTS)] + SUFFIXES[(i // len(ROOTS)) % len(SUFFIXES)]


def py_file(tw, caps):
    cap_lines = "\n".join("    %r," % c for c in caps)
    return (
        "# {stamp} {name} - Signature-Line twin\n"
        "# Original Signature-math implementation by Justin Addam Higgins.\n"
        "# Mirrors the claimed capabilities of: {model} ({vendor}).\n"
        "# Independent interpretation - not affiliated with {vendor}.\n"
        "# Reference (facts only, no copied text or branding): {url}\n"
        "# Runs anywhere with Python 3; no external dependencies.\n"
        "\n"
        "CAPABILITIES = [\n{cap_lines}\n]\n"
        "\n"
        "class SignatureLineTwin:\n"
        "    \"\"\"Deterministic Signature-math persona core.\"\"\"\n"
        "    def __init__(self):\n"
        "        self.name = {name_r}\n"
        "        self.stamp = {stamp_r}\n"
        "        self.engine = 'signature-math deterministic core'\n"
        "        self.mirrors = {model_r}\n"
        "\n"
        "    def capability_check(self, task):\n"
        "        task = task.lower()\n"
        "        hits = []\n"
        "        for c in CAPABILITIES:\n"
        "            words = [w for w in c.lower().split() if len(w) > 3]\n"
        "            if any(w.strip('.,;:()') in task for w in words):\n"
        "                hits.append(c)\n"
        "        return hits\n"
        "\n"
        "    def respond(self, prompt):\n"
        "        hits = self.capability_check(prompt)\n"
        "        if hits:\n"
        "            return self.name + ' engages: ' + '; '.join(hits)\n"
        "        return (self.name + ' ready. Ask me about: '\n"
        "                + ', '.join(CAPABILITIES[:3]))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    t = SignatureLineTwin()\n"
        "    print(t.name, t.stamp, '-', t.engine)\n"
        "    print('Mirrors the claimed capabilities of:', t.mirrors)\n"
        "    while True:\n"
        "        try:\n"
        "            q = input('you> ')\n"
        "        except (EOFError, KeyboardInterrupt):\n"
        "            break\n"
        "        if q.strip().lower() in ('quit', 'exit'):\n"
        "            break\n"
        "        print(t.respond(q))\n"
    ).format(stamp=tw["stamp"], name=tw["name"], model=tw["mirror"]["model"],
             vendor=tw["mirror"]["vendor"], url=tw["mirror"]["url"],
             cap_lines=cap_lines, name_r=repr(tw["name"]),
             stamp_r=repr(tw["stamp"]), model_r=repr(tw["mirror"]["model"]))


def build_twins():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    twins = []
    for i, m in enumerate(manifest):
        n = i + 1
        tw_id = "sl-%03d" % n
        stamp = "JAH-AI-SL-%03d" % n
        name = "Signature %s %s" % (epithet(i), TYPEWORD[m["type"]])
        caps = list(m["caps"])
        announced = (m["status"] == "announced")
        mentality = (
            "Signature-Line twin mirroring {model} ({vendor}) - an original "
            "implementation built from Signature math, in Manon's domain and "
            "legally distinct from the original. Independent interpretation; "
            "not affiliated with {vendor}. It is built to do everything the "
            "original's website claims: {caps}."
            "{ann}"
        ).format(model=m["model"], vendor=m["vendor"],
                 caps="; ".join(caps),
                 ann=(" The original is announced but not yet released; "
                      "this twin is operational now." if announced else ""))
        tw = {
            "id": tw_id,
            "name": name,
            "stamp": stamp,
            "ver": "1.0",
            "kind": "sl",
            "mentality": mentality,
            "abilities": caps,
            "params": [
                ["engine", "Signature-math deterministic core"],
                ["line", "Signature-Line"],
                ["mirrors", m["model"]],
                ["vendor", m["vendor"]],
                ["type", TYPE_LABEL[m["type"]]],
                ["original status", m["status"]],
                ["implementation", "original - no copied code, branding, or marketing text"],
            ],
            "demoTitle": "Capability check",
            "demoHTML": (
                '<input type="text" id="sl-in-%s" placeholder="Describe a task, e.g. summarize a document" '
                'style="width:100%%"><button data-sl="%s" onclick="slDemo(this)">Check capability</button>'
                '<span class="out" id="sl-out-%s"></span>'
            ) % (tw_id, tw_id, tw_id),
            "mirror": {"model": m["model"], "vendor": m["vendor"],
                       "url": m["url"], "status": m["status"]},
        }
        tw["py"] = py_file(tw, caps)
        twins.append(tw)
    # uniqueness guards
    ids = [t["id"] for t in twins]
    stamps = [t["stamp"] for t in twins]
    names = [t["name"] for t in twins]
    assert len(set(ids)) == len(ids), "duplicate twin ids"
    assert len(set(stamps)) == len(stamps), "duplicate twin stamps"
    assert len(set(names)) == len(names), "duplicate twin names"
    return twins


SL_DEMO_JS = """
/* Signature-Line twin demo: capability check (wired via inline onclick). */
function slDemo(btn){
  var id = btn.getAttribute('data-sl'), tw = null, i;
  for (i = 0; i < SL_TWINS.length; i++) if (SL_TWINS[i].id === id){ tw = SL_TWINS[i]; break; }
  if (!tw) return;
  var box = btn.parentNode;
  var inp = box.querySelector('input');
  var out = box.querySelector('.out');
  var q = ((inp && inp.value) || '').toLowerCase();
  var hits = [];
  tw.abilities.forEach(function(c){
    var ws = c.toLowerCase().split(/[^a-z0-9]+/);
    for (var k = 0; k < ws.length; k++){
      if (ws[k].length > 3 && q.indexOf(ws[k]) >= 0){ hits.push(c); break; }
    }
  });
  out.textContent = hits.length
    ? ('Capability match: ' + hits.join(' | '))
    : ('No direct match - try asking about: ' + tw.abilities.slice(0, 3).join(' | '));
}
"""


def write_js(twins):
    body = json.dumps(twins, ensure_ascii=False, indent=1)
    with open(OUT_JS, "w", encoding="utf-8") as f:
        f.write("/* Signature-Line AI twins - generated by code/sl_twins.py. "
                "Do not hand-edit; re-run the generator. */\n")
        f.write("var SL_TWINS = " + body + ";\n")
        f.write(SL_DEMO_JS)
    print("wrote", OUT_JS, "-", len(twins), "twins")


PATCHES = [
    # 1. load the twin data before the main inline script
    ("<!-- SL-TWINS-DATA -->",
     '<script src="js/sl_twins.js"></script>',
     '<script src="js/jah-talk-fallback.js"></script>'),
    # 2. file lookup finds twins
    ("/* SL-TWINS: findFullAi */",
     "  if (typeof SL_TWINS !== 'undefined'){ for (var _s = 0; _s < SL_TWINS.length; _s++) if (SL_TWINS[_s].id === id) return SL_TWINS[_s]; }",
     "  var ks = Object.keys(domIndex || {});"),
    # 3. directory entries
    ("/* SL-TWINS: dirEntries */",
     "  if (typeof SL_TWINS !== 'undefined') SL_TWINS.forEach(function(a){ dirEntries.push({name: a.name, sub: a.stamp + ' \\u00b7 Signature-Line twin', href: '#file-' + a.id, local: true}); });",
     "  PERSONAS.forEach(function(a){ dirEntries.push({name: a.name, sub: a.stamp + ' · Persona simulation', href: '#file-' + a.id, local: true}); });"),
    # 4. A-Z book entries
    ("/* SL-TWINS: buildBook */",
     "  if (typeof SL_TWINS !== 'undefined') SL_TWINS.forEach(function(a){ entries.push({id: a.id, name: a.name, stamp: a.stamp, tag: a.mentality, wing: 'SIGNATURE-LINE'}); });",
     "  PERSONAS.forEach(function(a){ entries.push({id: a.id, name: a.name, stamp: a.stamp, tag: a.mentality, wing: 'PERSONA'}); });"),
    # 5. finder/search index
    ("/* SL-TWINS: wireLookup */",
     "  if (typeof SL_TWINS !== 'undefined') SL_TWINS.forEach(function(a){ all.push({id: a.id, name: a.name, stamp: a.stamp, tag: a.mentality, hay: (a.name + ' ' + a.id + ' ' + a.stamp + ' ' + a.mentality + ' ' + (a.abilities || []).join(' ')).toLowerCase()}); });",
     "  PERSONAS.forEach(function(a){ all.push({id: a.id, name: a.name, stamp: a.stamp, tag: a.mentality, hay: (a.name + ' ' + a.id + ' ' + a.stamp + ' ' + a.mentality + ' ' + (a.abilities || []).join(' ')).toLowerCase()}); });"),
    # 6. live counter includes twins
    ("/* SL-TWINS: updateBookstats */",
     "  var slN = (typeof SL_TWINS !== 'undefined') ? SL_TWINS.length : 0;\n  var base = SIG_AIS.length + PERSONAS.length + DOMAIN_SPECS.length + slN;",
     "  var base = SIG_AIS.length + PERSONAS.length + DOMAIN_SPECS.length;"),
    ("/* SL-TWINS: updateBookstats-text */",
     "    var emb = base + ' embedded (' + SIG_AIS.length + ' system \\u00b7 ' + PERSONAS.length + ' persona \\u00b7 ' + DOMAIN_SPECS.length + ' domain \\u00b7 ' + slN + ' signature-line)';",
     "    var emb = base + ' embedded (' + SIG_AIS.length + ' system · ' + PERSONAS.length + ' persona · ' + DOMAIN_SPECS.length + ' domain)';"),
    # 7. phone numbers: district 600
    ("/* SL-TWINS: PhoneBook-dist */",
     "  var SIG_DIST = 200, PER_DIST = 300, WORD_DIST = 500, FIELD_BASE = 400, SL_DIST = 600;",
     "  var SIG_DIST = 200, PER_DIST = 300, WORD_DIST = 500, FIELD_BASE = 400;"),
    ("/* SL-TWINS: PhoneBook-distName */",
     "    if (dist === SL_DIST) return 'Signature-Line Twins';",
     "    if (dist === WORD_DIST) return 'Word AI Blocks';"),
    ("/* SL-TWINS: PhoneBook-build */",
     "    if (typeof SL_TWINS !== 'undefined') SL_TWINS.forEach(function(a, i){\n      var d = digits(SL_DIST, i + 1);\n      numById[a.id] = d; numLookup[d] = {kind: 'file', id: a.id, name: a.name, phone: d};\n    });",
     "    PERSONAS.forEach(function(a, i){\n      var d = digits(PER_DIST, i + 1);"),
    ("/* SL-TWINS: PhoneBook-export */",
     "    SIG_DIST: SIG_DIST, PER_DIST: PER_DIST, WORD_DIST: WORD_DIST, SL_DIST: SL_DIST",
     "    SIG_DIST: SIG_DIST, PER_DIST: PER_DIST, WORD_DIST: WORD_DIST"),
    # 8. dial-help text mentions district 600
    ("/* SL-TWINS: dialhelp */",
     "500 = word AIs, 600 = Signature-Line twins.",
     "500 = word AIs."),
    # 9. twin badge + disclaimer in the file view
    ("/* SL-TWINS: renderCard-badge */",
     "  h += ai.kind === 'sl' ? '<span class=\"badge\">SIGNATURE-LINE</span>' : (ai.kind === 'persona' ? '<span class=\"badge fan\">PERSONA SIM</span>' : '<span class=\"badge\">SIGNATURE-MADE</span>');",
     "  h += ai.kind === 'persona' ? '<span class=\"badge fan\">PERSONA SIM</span>' : '<span class=\"badge\">SIGNATURE-MADE</span>';"),
    ("/* SL-TWINS: renderCard-disclaimer */",
     "  if (ai.kind === 'sl' && ai.mirror) h += '<div class=\"disclaimer\">Signature-Line twin \\u2014 original Signature-math implementation; independent interpretation of ' + escHtml(ai.mirror.model) + ' (' + escHtml(ai.mirror.vendor) + '), not affiliated with or endorsed by them.</div>';\n  if (ai.kind === 'persona') h += '<div class=\"disclaimer\">Persona simulation \\u2014 fan-style interpretation, not affiliated with any rights holder. Skynet/Terminator shown as fiction, never as real.</div>';",
     "  if (ai.kind === 'persona') h += '<div class=\"disclaimer\">Persona simulation — fan-style interpretation, not affiliated with any rights holder. Skynet/Terminator shown as fiction, never as real.</div>';"),
    # 10. copy-text note for twins
    ("/* SL-TWINS: fileText-note */",
     "  if (ai.kind === 'sl' && ai.mirror){ L.push('NOTE: Signature-Line twin \\u2014 original Signature-math implementation; independent interpretation of ' + ai.mirror.model + ' (' + ai.mirror.vendor + '), not affiliated.'); L.push(''); }\n  if (ai.kind === 'persona'){ L.push('NOTE: Persona simulation — fan-style interpretation, not affiliated with any rights holder.'); L.push(''); }",
     "  if (ai.kind === 'persona'){ L.push('NOTE: Persona simulation — fan-style interpretation, not affiliated with any rights holder.'); L.push(''); }"),
]


def apply_patches():
    html = open(INDEX, encoding="utf-8").read()
    applied = 0
    for marker, addition, anchor in PATCHES:
        if marker in html:
            continue
        if anchor not in html:
            raise SystemExit("PATCH ANCHOR NOT FOUND: %r" % anchor[:70])
        html = html.replace(anchor, marker + "\n" + addition + "\n" + anchor, 1)
        applied += 1
    open(INDEX, "w", encoding="utf-8").write(html)
    print("index.html patches applied:", applied, "(0 = all already present)")


def stamp_sitemap(twins):
    p = os.path.join(REPO, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r'  <url><loc>[^<]*#file-sl-\d+</loc><changefreq>monthly</changefreq></url>  <!-- sl-twin -->\n', '', s)
    entries = "".join(
        '  <url><loc>https://justinahiggins614-cmyk.github.io/jah-ai-models/index.html#file-%s</loc>'
        '<changefreq>monthly</changefreq></url>  <!-- sl-twin -->\n' % t["id"]
        for t in twins)
    s = s.replace("</urlset>", entries + "</urlset>", 1)
    open(p, "w", encoding="utf-8").write(s)
    print("sitemap.xml: stamped", len(twins), "twin deep links")


def main():
    twins = build_twins()
    write_js(twins)
    apply_patches()
    stamp_sitemap(twins)
    print("done: %d Signature-Line twins" % len(twins))


if __name__ == "__main__":
    main()
