#!/usr/bin/env python3
"""Duplicate-ID checker for the Signature AI Telephone Book.

Every embedded AI must have a unique stamp (JAH-AI-SIG/PER/DOM-###) and a
unique file id (used for #file-<id> deep links and downloads). Also checks
ai-catalog.json records for duplicate IDs.

Data arrays are parsed with node (same as count_check.py) — regexes proved
unreliable against the nested chat-data arrays inside DOMAIN_SPECS rows.

Re-runnable:  python3 code/qa/dup_id_check.py
Exit code 0 = no duplicates, 1 = duplicates found.
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

# literal stamps in the SIG_AIS / PERSONAS arrays
stamps = re.findall(r"stamp:'(JAH-AI-[A-Z]+-\d+)'", html)

start = html.index("var SIG_AIS")
end = html.index("function domainParams")
js = html[start:end] + """
var out = {
  sigIds: SIG_AIS.map(function(a){ return a.id; }),
  perIds: PERSONAS.map(function(a){ return a.id; }),
  domSids: DOMAIN_SPECS.map(function(s){ return s[0]; }),
  domStamps: DOMAIN_SPECS.map(function(s, i){ return 'JAH-AI-DOM-' + String(i+1).padStart(3, '0'); })
};
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

stamps += live["domStamps"]
all_ids = live["sigIds"] + live["perIds"] + ["dom-" + s for s in live["domSids"]]

catalog = json.load(open(os.path.join(REPO, "ai-catalog.json"), encoding="utf-8"))
cat_ids = [r["ID"] for r in catalog["records"]]

problems = []


def check(label, items):
    seen, dupes = set(), set()
    for it in items:
        if it in seen:
            dupes.add(it)
        seen.add(it)
    print("  %-24s n=%d unique=%d %s" % (label, len(items), len(seen),
                                         "OK" if not dupes else "DUPES: %s" % sorted(dupes)))
    if dupes:
        problems.append("%s duplicates: %s" % (label, sorted(dupes)))


check("embedded stamps", stamps)
check("embedded file ids", all_ids)
check("ai-catalog.json IDs", cat_ids)

# cross-check: every catalog ID must exist as a stamp in the page
missing = [c for c in cat_ids if c not in stamps]
if missing:
    problems.append("catalog IDs missing from page: %s" % missing)
    print("  catalog IDs all present in page: %s" % missing)
else:
    print("  catalog IDs all present in page: OK")

print()
if problems:
    print("DUPLICATES/PROBLEMS (%d):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("NO DUPLICATE IDS — %d stamps, %d file ids, %d catalog records" % (len(set(stamps)), len(set(all_ids)), len(cat_ids)))
