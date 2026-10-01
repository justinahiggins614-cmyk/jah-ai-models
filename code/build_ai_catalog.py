#!/usr/bin/env python3
"""Build ai-catalog.json: machine-readable records for every embedded AI file.

Parses the actual data arrays out of index.html (SIG_AIS, PERSONAS, DOMAIN_SPECS
+ the domIndex builder) with node, then emits one record per AI with
ID/NAME/TYPE/DESCRIPTION/STATUS/VERSION/SOURCE/RELATIONSHIPS/HASH/ARTIFACTS.

Re-run after any data change:  python3 code/build_ai_catalog.py
"""
import json, subprocess, hashlib, datetime, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SITE = "https://justinahiggins614-cmyk.github.io/jah-ai-models/"

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
import tempfile
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
    tf.write(js)
    tf_path = tf.name
node = subprocess.run(["node", tf_path], capture_output=True, text=True)
os.unlink(tf_path)
if node.returncode != 0:
    raise SystemExit("node parse failed:\n" + node.stderr)
rows = json.loads(node.stdout)

records = []
seen = set()
for r in rows:
    o = r["obj"]
    stamp = o["stamp"]
    if stamp in seen:
        raise SystemExit("DUPLICATE STAMP: " + stamp)
    seen.add(stamp)
    aid = o.get("sid") or o["id"]
    if r["embed"] == "sig":
        typ, role, file_id = "system", "SYSTEM MODEL", o["id"]
    elif r["embed"] == "persona":
        typ, role, file_id = "persona", "PERSONA SIM", o["id"]
    else:
        typ, role, file_id = "domain", "ASSISTANT", o["id"]
    abilities = o.get("abilities") or []
    desc = o.get("mentality", "")
    rel = {}
    if r["embed"] == "persona":
        rel["disclaimer"] = "fan-style simulation, not affiliated with any rights holder"
    if r["embed"] == "domain":
        rel["domain"] = o.get("domain", "")
        rel["demo_kind"] = o.get("demoKind", "")
    canon = json.dumps([stamp, o["name"], typ, desc, abilities], sort_keys=True)
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    records.append({
        "ID": stamp,
        "NAME": o["name"],
        "TYPE": typ,
        "DESCRIPTION": desc,
        "STATUS": "PUBLISHED",
        "VERSION": o.get("ver", "1.0"),
        "ROLE": role,
        "SOURCE": "embedded in index.html — Signature-made by Justin Addam Higgins",
        "RELATIONSHIPS": rel,
        "HASH": "sha256:" + digest,
        "ARTIFACTS": {
            "download": file_id + ".py",
            "deep_link": "#file-" + file_id,
            "live_url": SITE + "#file-" + file_id,
        },
    })

catalog = {
    "site": "The Signature AI Telephone Book",
    "site_url": SITE,
    "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "for_bots": "Machine-readable catalog of the embedded AI files. Word AIs (JAH-AI-WORD-######) are lazy-loaded from the Spec Catalog word-AI index; hybrid files (JAH-AI-MIX-######) are generated deterministically on demand.",
    "counts": {
        "embedded_total": len(records),
        "system": sum(1 for x in records if x["TYPE"] == "system"),
        "persona": sum(1 for x in records if x["TYPE"] == "persona"),
        "domain": sum(1 for x in records if x["TYPE"] == "domain"),
    },
    "wordai_index": "https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz",
    "records": records,
}
out_path = os.path.join(REPO, "ai-catalog.json")
json.dump(catalog, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("wrote", out_path, "records:", len(records))
