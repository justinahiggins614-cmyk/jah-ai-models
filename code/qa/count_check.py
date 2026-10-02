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

print()
if problems:
    print("MISMATCHES (%d):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("ALL COUNTS AGREE — embedded leg exact at %d" % total_live)
