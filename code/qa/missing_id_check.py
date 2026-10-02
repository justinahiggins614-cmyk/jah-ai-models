#!/usr/bin/env python3
"""Missing-ID checker for the Signature AI Telephone Book.

Embedded AI stamps are sequential per wing:
  JAH-AI-SIG-001..011   (11 system AIs)
  JAH-AI-PER-001..006   (6 persona AIs)
  JAH-AI-DOM-001..243   (243 domain AIs, generated in index.html)
Reports any gaps in the sequences. Gaps are reported, not auto-fixed —
a gap may be intentional, but it should be a conscious choice.

Re-runnable:  python3 code/qa/missing_id_check.py
Exit code 0 = sequences complete, 1 = gaps found.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
stamps = re.findall(r"stamp:'(JAH-AI-[A-Z]+-\d+)'", html)

# Domain stamps are generated in JS (not literal in the HTML):
#   stamp: 'JAH-AI-DOM-' + String(i+1).padStart(3,'0')
# so the DOM sequence is complete exactly when DOMAIN_SPECS has 243 rows.
if re.search(r"stamp:\s*'JAH-AI-DOM-'\s*\+\s*String\(i\+1\)", html):
    dom_rows = re.findall(r"^\['([a-z0-9\-]+)',", html, re.M)
    # only count rows inside the DOMAIN_SPECS array block
    block = html[html.index("var DOMAIN_SPECS"):html.index("var domIndex")]
    dom_rows = re.findall(r"^\['([a-z0-9\-]+)',", block, re.M)
    stamps += ["JAH-AI-DOM-%03d" % (i + 1) for i in range(len(dom_rows))]
else:
    print("WARNING: DOM stamp generator expression not found — sequences may have changed shape")

wings = {}
for s in stamps:
    kind, num = s.rsplit("-", 1)
    wings.setdefault(kind, []).append(int(num))

EXPECT = {"JAH-AI-SIG": 11, "JAH-AI-PER": 6, "JAH-AI-DOM": 243}
problems = []
for wing, want in sorted(EXPECT.items()):
    have = sorted(set(wings.get(wing, [])))
    missing = [n for n in range(1, want + 1) if n not in have]
    extra = [n for n in have if n > want]
    status = "OK" if not missing and not extra else "GAP"
    print("  %-12s have=%d want=%d %s%s%s" % (
        wing, len(have), want, status,
        (" missing=" + ",".join(map(str, missing))) if missing else "",
        (" extra=" + ",".join(map(str, extra))) if extra else ""))
    if missing:
        problems.append("%s missing numbers: %s" % (wing, missing))
    if extra:
        problems.append("%s numbers beyond %d: %s" % (wing, want, extra))

print()
if problems:
    print("GAPS (%d):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("ALL ID SEQUENCES COMPLETE — 11 SIG + 6 PER + 243 DOM")
