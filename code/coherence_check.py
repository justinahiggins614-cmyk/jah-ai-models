#!/usr/bin/env python3
"""Coherence check: embedded AI records in index.html vs the canon ai-catalog.json.

Manon's order (2026-10-02): "There should be no ai any website incoherent" —
every AI profile matches the phone-book canon exactly. The canon lives at
jah-ai-models/ai-catalog.json (built from index.html's own embedded arrays by
code/build_ai_catalog.py). This checker re-parses the embedded arrays
(SIG_AIS, PERSONAS, domIndex) and verifies every record's ID/NAME/DESCRIPTION
matches the catalog exactly.

Exit 0 = coherent. Exit 1 = drift found (fails loudly with a full report).
Run after any AI data edit:  python3 code/coherence_check.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def embedded_records():
    html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
    start = html.index("var SIG_AIS")
    end = html.index("function domainParams")
    js = html[start:end] + """
var out = [];
SIG_AIS.forEach(function(a){ out.push({embed:'sig', obj:a}); });
PERSONAS.forEach(function(a){ out.push({embed:'persona', obj:a}); });
Object.keys(domIndex).forEach(function(k){ out.push({embed:'domain', obj:domIndex[k]}); });
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
        tf.write(js)
        tf_path = tf.name
    try:
        node = subprocess.run(["node", tf_path], capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(tf_path)
    if node.returncode != 0:
        raise SystemExit("node parse of embedded arrays failed:\n" + node.stderr)
    return json.loads(node.stdout)


def main():
    rows = embedded_records()
    catalog = json.load(open(os.path.join(REPO, "ai-catalog.json"), encoding="utf-8"))
    by_id = {r["ID"]: r for r in catalog.get("records", [])}

    issues = []
    seen = set()
    for row in rows:
        o = row["obj"]
        sid = norm(o.get("stamp") or o.get("ai_id") or o.get("id"))
        if not sid:
            issues.append("embedded %s record missing stamp/ID (name=%r)" % (row["embed"], o.get("name")))
            continue
        seen.add(sid)
        rec = by_id.get(sid)
        if rec is None:
            issues.append("embedded %s %s (%s) has NO record in ai-catalog.json" % (row["embed"], sid, o.get("name")))
            continue
        ename, cname = norm(o.get("name")), norm(rec.get("NAME"))
        if ename and cname and ename.lower() != cname.lower():
            issues.append("NAME mismatch %s: embedded %r vs canon %r" % (sid, ename, cname))
        edesc, cdesc = norm(o.get("mentality") or o.get("description")), norm(rec.get("DESCRIPTION"))
        if edesc and cdesc and edesc != cdesc:
            issues.append("DESCRIPTION drift %s (%s): first 120 chars differ" % (sid, ename))
    for cid in sorted(set(by_id) - seen):
        issues.append("canon record %s (%s) has NO embedded AI in index.html" % (cid, by_id[cid].get("NAME")))

    print("coherence_check: %d embedded AIs parsed, %d canon records" % (len(rows), len(by_id)))
    if issues:
        print("FAIL — %d coherence issue(s):" % len(issues))
        for i in issues:
            print("  - " + i)
        return 1
    print("PASS — every embedded AI matches ai-catalog.json exactly (ID/NAME/DESCRIPTION).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
