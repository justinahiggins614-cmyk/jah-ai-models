#!/usr/bin/env python3
"""Duplicate-ID checker for the Signature AI Telephone Book.

Every embedded AI must have a unique stamp (JAH-AI-SIG/PER/DOM-###) and a
unique file id (used for #file-<id> deep links and downloads). Also checks
ai-catalog.json records for duplicate IDs.

Re-runnable:  python3 code/qa/dup_id_check.py
Exit code 0 = no duplicates, 1 = duplicates found.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()

stamps = re.findall(r"stamp:'(JAH-AI-[A-Z]+-\d+)'", html)
# Domain stamps are generated in JS: stamp: 'JAH-AI-DOM-' + String(i+1).padStart(3,'0')
if re.search(r"stamp:\s*'JAH-AI-DOM-'\s*\+\s*String\(i\+1\)", html):
    block = html[html.index("var DOMAIN_SPECS"):html.index("var domIndex")]
    dom_rows = re.findall(r"^\['([a-z0-9\-]+)',", block, re.M)
    stamps += ["JAH-AI-DOM-%03d" % (i + 1) for i in range(len(dom_rows))]
# AI file ids: {id:'...'} inside the SIG_AIS / PERSONAS data arrays only
sig_block = html[html.index("var SIG_AIS"):html.index("var PERSONAS")]
per_block = html[html.index("var PERSONAS"):html.index("var DOMAIN_SPECS")]
file_ids = re.findall(r"\{id:'([a-z0-9\-]+)'", sig_block) + re.findall(r"\{id:'([a-z0-9\-]+)'", per_block)
# domain file ids are generated as 'dom-' + row sid; parse only the DOMAIN_SPECS block
block = html[html.index("var DOMAIN_SPECS"):html.index("var domIndex")]
dom_rows = re.findall(r"^\['([a-z0-9\-]+)',", block, re.M)
dom_ids = ["dom-" + r for r in dom_rows]
all_ids = file_ids + dom_ids
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
    print("  catalog IDs missing from page: %s" % missing)
else:
    print("  catalog IDs all present in page: OK")

print()
if problems:
    print("DUPLICATES/PROBLEMS (%d):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("NO DUPLICATE IDS — %d stamps, %d file ids, %d catalog records" % (len(set(stamps)), len(set(all_ids)), len(cat_ids)))
