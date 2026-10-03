#!/usr/bin/env python3
"""Count-vs-database checker for the Signature AI Phone Book.

Ground truth = the data arrays parsed out of index.html with node
(SIG_AIS + PERSONAS + DOMAIN_SPECS). Compares against:
  * ai-catalog.json  (embedded records machine catalog)
  * api.json         (records_embedded + records_embedded_breakdown)
  * hero breakdown text baked into index.html

No counts are hardcoded: expectations are DERIVED from the live data arrays
(2026-10-03 fix: the old script hardcoded 260/243 and went stale when the
domain leg grew to 253). The word-AI leg lives in the signature-one-archive
repo and is fetched live by the page at runtime; ai-catalog.json/api.json carry
a baked snapshot (wordai_index_records as of wordai_as_of); the hero shows
that snapshot until the live index loads.

Re-runnable:  python3 code/qa/count_check.py
Exit code 0 = counts agree, 1 = mismatch.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
start = html.index("var SIG_AIS")
end = html.index("function domainParams")
js = html[start:end] + """
var out = {sig: SIG_AIS.length, per: PERSONAS.length, dom: DOMAIN_SPECS.length};
console.log(JSON.stringify(out));
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
    tf.write(js)
    tf_path = tf.name
node = subprocess.run(["node", tf_path], capture_output=True, text=True)
os.unlink(tf_path)
if node.returncode != 0:
    sys.exit("node parse failed:\n" + node.stderr)
live = json.loads(node.stdout)
total_live = live["sig"] + live["per"] + live["dom"]

catalog = json.load(open(os.path.join(REPO, "ai-catalog.json"), encoding="utf-8"))
api = json.load(open(os.path.join(REPO, "api.json"), encoding="utf-8"))

problems = []


def expect(label, got, want):
    ok = got == want
    print("  %-30s got=%s want=%s  %s" % (label, got, want, "OK" if ok else "MISMATCH"))
    if not ok:
        problems.append("%s: got %s, want %s" % (label, got, want))


print("live data arrays in index.html: %d system / %d persona / %d domain = %d embedded"
      % (live["sig"], live["per"], live["dom"], total_live))

print("ai-catalog.json:")
cc = catalog["counts"]
expect("catalog embedded_total", cc["embedded_total"], total_live)
expect("catalog system", cc["system"], live["sig"])
expect("catalog persona", cc["persona"], live["per"])
expect("catalog domain", cc["domain"], live["dom"])
expect("catalog records length", len(catalog["records"]), total_live)
expect("catalog published = emb + wordai",
       cc["published_total"], total_live + int(cc["wordai_index_records"]))

print("api.json (same source as catalog):")
expect("api records_embedded", api["records_embedded"], total_live)
bd = api["records_embedded_breakdown"]
expect("api breakdown system", bd["system"], live["sig"])
expect("api breakdown persona", bd["persona"], live["per"])
expect("api breakdown domain", bd["domain"], live["dom"])
expect("api wordai == catalog wordai",
       int(api["wordai_index_records"]), int(cc["wordai_index_records"]))
expect("api published == catalog published",
       int(api["records_published_total"]), int(cc["published_total"]))
expect("api has schema_version", bool(api.get("schema_version")), True)
expect("api has catalog_revision", bool(api.get("catalog_revision")), True)
print("  note: wordai snapshot=%s as of %s (live index drifts on the word-spec drip; page derives the live total at runtime)"
      % (api.get("wordai_index_records"), api.get("records_as_of")))

print("static hero baked into index.html (curl-visible for crawlers):")
hero_html = html
hero_m = re.search(r'<div class="bookbreak"><span id="aibreakdown">(.*?)</span></div>', hero_html, re.S)
if not hero_m:
    problems.append("hero static breakdown block missing from index.html")
    print("  hero breakdown block: MISSING")
else:
    hero = hero_m.group(1)
    expect("hero shows system count", ("%d system" % live["sig"]) in hero, True)
    expect("hero shows persona count", ("%d persona" % live["per"]) in hero, True)
    expect("hero shows domain count", ("%d domain" % live["dom"]) in hero, True)
    expect("hero word-AI count",
           re.search(r"\+ ([\d,]+) word-AIs", hero).group(1).replace(",", ""),
           str(cc["wordai_index_records"]))
    expect("hero total", re.search(r"PUBLISHED AI FILES: <b>([\d,]+)</b>", hero).group(1).replace(",", ""),
           str(total_live + int(cc["wordai_index_records"])))
    as_of = re.search(r"(?:as of|Last synchronized) (\d{4}-\d{2}-\d{2})", hero)
    expect("hero has sync stamp", bool(as_of), True)
    if as_of:
        expect("hero sync date", as_of.group(1), cc["wordai_as_of"])
    hero_total = re.search(r'<span id="aicount"><b>([\d,]+)</b></span>', hero_html).group(1).replace(",", "")
    expect("hero headline count", hero_total, str(total_live + int(cc["wordai_index_records"])))

print("duplicate ID scan:")
seen = {}
dupes = 0
for r in catalog["records"]:
    if r["ID"] in seen:
        dupes += 1
        problems.append("duplicate ID: " + r["ID"])
    seen[r["ID"]] = 1
expect("duplicate IDs", dupes, 0)

print()
if problems:
    print("MISMATCHES (%d):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("ALL COUNTS AGREE — embedded leg exact at %d, published %d (as of %s)"
      % (total_live, cc["published_total"], cc["wordai_as_of"]))
