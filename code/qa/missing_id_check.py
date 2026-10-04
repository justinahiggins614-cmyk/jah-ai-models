#!/usr/bin/env python3
"""Missing-ID checker for the Signature AI Telephone Book.

Embedded AI stamps are sequential per wing:
  JAH-AI-SIG-001..NNN   (system AIs)
  JAH-AI-PER-001..NNN   (persona AIs)
  JAH-AI-DOM-001..NNN   (domain AIs, generated in index.html)
Expected lengths are DERIVED from the live data arrays via node (2026-10-03
fix: the old script hardcoded 243 domain AIs and went stale when the leg grew
to 253). Reports any gaps in the sequences. Gaps are reported, not auto-fixed.

Re-runnable:  python3 code/qa/missing_id_check.py
Exit code 0 = sequences complete, 1 = gaps found.
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
twin_src = open(os.path.join(REPO, "js", "sl_twins.js"), encoding="utf-8").read()
js = twin_src + "\n" + html[start:end] + """
console.log(JSON.stringify({
  sig: SIG_AIS.length, per: PERSONAS.length, dom: DOMAIN_SPECS.length, sl: SL_TWINS.length,
  domStamps: DOMAIN_SPECS.map(function(s, i){ return 'JAH-AI-DOM-' + String(i+1).padStart(3, '0'); }),
  slStamps: SL_TWINS.map(function(a){ return a.stamp; })
}));
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
    tf.write(js)
    tf_path = tf.name
node = subprocess.run(["node", tf_path], capture_output=True, text=True)
os.unlink(tf_path)
if node.returncode != 0:
    sys.exit("node parse failed:\n" + node.stderr)
live = json.loads(node.stdout)

stamps = re.findall(r"stamp:'(JAH-AI-[A-Z]+-\d+)'", html)
stamps += live["domStamps"]
stamps += live["slStamps"]

wings = {}
for s in stamps:
    kind, num = s.rsplit("-", 1)
    wings.setdefault(kind, []).append(int(num))

EXPECT = {"JAH-AI-SIG": live["sig"], "JAH-AI-PER": live["per"], "JAH-AI-DOM": live["dom"],
          "JAH-AI-SL": live["sl"]}
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
print("ALL ID SEQUENCES COMPLETE — %d SIG + %d PER + %d DOM" % (live["sig"], live["per"], live["dom"]))
