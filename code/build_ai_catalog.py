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

# Word-AI leg: live snapshot from the authoritative index in signature-one-archive
# (the same file the page's hero counter fetches). Baked with an as-of date.
def user_date():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.date.today().strftime("%Y-%m-%d")
wordai_snapshot = {"records": 0, "as_of": user_date()}
try:
    import gzip, urllib.request
    req = urllib.request.Request(
        "https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz",
        headers={"User-Agent": "JAH-QA-build-catalog/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        idx = json.loads(gzip.decompress(r.read()).decode("utf-8"))
    wordai_snapshot["records"] = len(idx)
except Exception as e:  # noqa: BLE001 - index unreachable; bake last-known snapshot
    try:
        prev = json.load(open(os.path.join(REPO, "ai-catalog.json"), encoding="utf-8"))
        wordai_snapshot = {"records": int(prev["counts"].get("wordai_index_records", 0)),
                           "as_of": prev["counts"].get("wordai_as_of", wordai_snapshot["as_of"])}
        print("wordai index unreachable (%s); keeping previous snapshot %s" % (e, wordai_snapshot))
    except Exception:
        print("wordai index unreachable (%s); snapshot stays 0" % e)

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
        "wordai_index_records": wordai_snapshot["records"],
        "wordai_as_of": wordai_snapshot["as_of"],
        "published_total": len(records) + wordai_snapshot["records"],
    },
    "wordai_index": "https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz",
    "records": records,
}
out_path = os.path.join(REPO, "ai-catalog.json")
json.dump(catalog, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("wrote", out_path, "records:", len(records))

# ---- api.json: same single source of truth (items 151-160 of the fix list).
# Never maintain totals by hand again; this builder owns both files.
counts = catalog["counts"]
api_path = os.path.join(REPO, "api.json")
prev_api = {}
try:
    prev_api = json.load(open(api_path, encoding="utf-8"))
except Exception:
    pass
api = {
    "schema_version": "1.1",
    "catalog_revision": int(prev_api.get("catalog_revision", 0)) + 1,
    "generated_at": catalog["generated_at"],
    "records_as_of": wordai_snapshot["as_of"],
    "site": "The Signature AI Telephone Book",
    "site_url": SITE,
    "creator": prev_api.get("creator", "Justin Addam Higgins"),
    "description": prev_api.get("description", ""),
    "for_bots": prev_api.get("for_bots", ""),
    "counts": {
        "embedded_total": counts["embedded_total"],
        "embedded_breakdown": {"system": counts["system"],
                                "persona": counts["persona"],
                                "domain": counts["domain"]},
        "wordai_index_records": counts["wordai_index_records"],
        "wordai_as_of": counts["wordai_as_of"],
        "published_total": counts["published_total"],
        "hybrid_space": {
            "possible_combinations": 1000000,
            "generated_on_demand": True,
            "note": "1,000,000 is the deterministic Mix Lab hybrid combination space. "
                    "Hybrids are generated on demand per device; they are NOT published files.",
        },
    },
    # legacy flat keys kept for existing consumers
    "records_embedded": counts["embedded_total"],
    "records_embedded_breakdown": {"system": counts["system"],
                                   "persona": counts["persona"],
                                   "domain": counts["domain"]},
    "wordai_index_records": counts["wordai_index_records"],
    "records_published_total": counts["published_total"],
    "hybrid_space": 1000000,
    "wordai_index": catalog["wordai_index"],
    "sitemap": SITE + "sitemap.xml",
    "raw_github_base": prev_api.get("raw_github_base",
        "https://raw.githubusercontent.com/justinahiggins614-cmyk/jah-ai-models/main/"),
    "deep_links": prev_api.get("deep_links", []),
    "endpoints": [
        {"path": "ai-catalog.json",
         "desc": "Machine-readable catalog of the %d embedded AI files: ID/NAME/TYPE/DESCRIPTION/STATUS/VERSION/ROLE/SOURCE/RELATIONSHIPS/HASH/ARTIFACTS." % counts["embedded_total"]},
        {"path": "api.json",
         "desc": "This manifest: counts, endpoints, deep links, schema version, catalog revision."},
    ],
    "note": prev_api.get("note", ""),
    "raw_example": prev_api.get("raw_example"),
}
json.dump(api, open(api_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("wrote", api_path, "revision", api["catalog_revision"])

# ---- stamp the static hero (crawler-visible) from the same source ----
hero_path = os.path.join(REPO, "index.html")
hero = open(hero_path, encoding="utf-8").read()
emb = counts["embedded_total"]
pub = counts["published_total"]
wa = counts["wordai_index_records"]
asof = counts["wordai_as_of"]
new_aicount = '<span id="aicount"><b>%s</b></span>' % format(pub, ",d")
hero = re.sub(r'<span id="aicount"><b>[\d,]+</b></span>', new_aicount, hero)
new_break = ('PUBLISHED AI FILES: <b>%s</b> = %d embedded (%d system &middot; %d persona &middot; %d domain) '
             '+ %s word-AIs &middot; Last synchronized %s &mdash; live count refreshes when the word-AI index loads'
             % (format(pub, ",d"), emb, counts["system"], counts["persona"], counts["domain"],
                format(wa, ",d"), asof))
hero = re.sub(r'<span id="aibreakdown">.*?</span>',
              '<span id="aibreakdown">' + new_break + '</span>', hero, count=1, flags=re.S)
open(hero_path, "w", encoding="utf-8").write(hero)
print("stamped hero: %s published (%d embedded + %d word-AIs), as of %s"
      % (format(pub, ",d"), emb, wa, asof))
