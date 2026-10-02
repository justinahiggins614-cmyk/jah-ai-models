#!/usr/bin/env python3
"""Count-vs-database checker for the Signature AI Telephone Book.

Ground truth = the data arrays parsed out of index.html with node
(SIG_AIS + PERSONAS + DOMAIN_SPECS). Compares against:
  * ai-catalog.json  (embedded records machine catalog)
  * api.json         (records_embedded + records_embedded_breakdown)
  * hero breakdown text expectations (11 system / 6 persona / 243 domain)

The word-AI leg lives in the signature-one-archive repo and is fetched live
by the page at runtime; api.json carries a snapshot (wordai_index_records).
This checker verifies the embedded leg is exact and reports the snapshot.

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

catalog = json.load(open(os.path.join(REPO, "ai-catalog.json"), encoding="utf-8"))
api = json.load(open(os.path.join(REPO, "api.json"), encoding="utf-8"))

problems = []


def expect(label, got, want):
    ok = got == want
    print("  %-28s got=%s want=%s  %s" % (label, got, want, "OK" if ok else "MISMATCH"))
    if not ok:
        problems.append("%s: got %s, want %s" % (label, got, want))


print("live data arrays in index.html:")
expect("system AIs", live["sig"], 11)
expect("persona AIs", live["per"], 6)
expect("domain AIs", live["dom"], 243)
total_live = live["sig"] + live["per"] + live["dom"]
expect("embedded total", total_live, 260)

print("ai-catalog.json:")
expect("catalog embedded_total", catalog["counts"]["embedded_total"], total_live)
expect("catalog system", catalog["counts"]["system"], live["sig"])
expect("catalog persona", catalog["counts"]["persona"], live["per"])
expect("catalog domain", catalog["counts"]["domain"], live["dom"])
expect("catalog records length", len(catalog["records"]), total_live)

print("api.json:")
expect("api records_embedded", api["records_embedded"], total_live)
bd = api["records_embedded_breakdown"]
expect("api breakdown system", bd["system"], live["sig"])
expect("api breakdown persona", bd["persona"], live["per"])
expect("api breakdown domain", bd["domain"], live["dom"])
print("  note: api wordai_index_records=%s is a snapshot as of %s (live index drifts on the word-spec drip; page derives the live total at runtime)"
      % (api.get("wordai_index_records"), api.get("records_as_of")))

print("static hero breakdown baked into index.html (curl-visible for crawlers):")
hero_html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
hero_m = re.search(r'<div class="bookbreak"><span id="aibreakdown">(.*?)</span></div>', hero_html, re.S)
if not hero_m:
    problems.append("hero static breakdown block missing from index.html")
    print("  hero breakdown block: MISSING")
else:
    hero = hero_m.group(1)
    expect("hero shows system 11", "11 system" in hero, True)
    expect("hero shows persona 6", "6 persona" in hero, True)
    expect("hero shows domain 243", "243 domain" in hero, True)
    expect("hero word-AI count", re.search(r"\+ ([\d,]+) word-AIs", hero).group(1).replace(",", ""),
           str(api.get("wordai_index_records")))
    expect("hero word-AI matches catalog snapshot", re.search(r"\+ ([\d,]+) word-AIs", hero).group(1).replace(",", ""),
           str(catalog["counts"].get("wordai_index_records")))
    expect("hero total", re.search(r"PUBLISHED AI FILES: <b>([\d,]+)</b>", hero).group(1).replace(",", ""),
           str(total_live + int(api.get("wordai_index_records"))))
    as_of = re.search(r"as of (\d{4}-\d{2}-\d{2})", hero)
    expect("hero has as-of stamp", bool(as_of), True)
    if as_of:
        expect("hero as-of date", as_of.group(1), catalog["counts"].get("wordai_as_of"))
    hero_total = re.search(r'<span id="aicount"><b>([\d,]+)</b></span>', hero_html).group(1).replace(",", "")
    expect("hero headline count", hero_total, str(total_live + int(api.get("wordai_index_records"))))

print()
if problems:
    print("MISMATCHES (%d):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("ALL COUNTS AGREE — embedded leg exact at %d" % total_live)
