#!/usr/bin/env python3
"""Build ai-catalog.json: machine-readable records for every embedded AI file.

Parses the actual data arrays out of index.html (SIG_AIS, PERSONAS, DOMAIN_SPECS
+ the domIndex builder) with node, then emits one record per AI with
ID/NAME/TYPE/DESCRIPTION/STATUS/VERSION/SOURCE/RELATIONSHIPS/HASH/ARTIFACTS.

This builder owns the count truth: after flushing ai-catalog.json + api.json it
stamps the hero counts in index.html AND rebuilds archive.html (code/build_archive.py)
from the JUST-WRITTEN catalog -- stamp AFTER the data flushes, never one run behind.

Re-run after any data change:  python3 code/build_ai_catalog.py
"""
import json, subprocess, hashlib, datetime, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SITE = "https://justinahiggins614-cmyk.github.io/jah-ai-models/"

html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()
start = html.index("var SIG_AIS")
end = html.index("function domainParams")
twin_src = open(os.path.join(REPO, "js", "sl_twins.js"), encoding="utf-8").read()
js = twin_src + "\n" + html[start:end] + """
var out = {rows: [], fields: []};
SIG_AIS.forEach(function(a,i){ out.rows.push({embed:'sig', idx:i, obj:a}); });
PERSONAS.forEach(function(a,i){ out.rows.push({embed:'persona', idx:i, obj:a}); });
SL_TWINS.forEach(function(a,i){ out.rows.push({embed:'sl', idx:i, obj:a}); });
var fieldSet = {};
DOMAIN_SPECS.forEach(function(s){ fieldSet[s[2]] = 1; });
out.fields = Object.keys(fieldSet).sort();
DOMAIN_SPECS.forEach(function(s,i){
  out.rows.push({embed:'domain', idx:i, field:s[2], obj:domIndex[s[0]]});
});
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
payload = json.loads(node.stdout)
rows = payload["rows"]
FIELDS = payload["fields"]


def _digits(dist, idx):
    return "1" + str(dist).zfill(3) + str(idx).zfill(7)


def _fmt_num(d):
    return d[0] + "-" + d[1:4] + "-" + d[4:]


# Signature numbers: same algorithm as PhoneBook.build() in index.html
# (1 + 3-digit district + 7-digit block; districts: 200 system, 300 persona,
#  400+ per domain field in sorted-field order, per-field sequence).
_FIELD_DIST = {f: 400 + i for i, f in enumerate(FIELDS)}
_per_field = {}
for _r in rows:
    _e = _r["embed"]
    if _e == "sig":
        _r["signum"] = _fmt_num(_digits(200, _r["idx"] + 1))
    elif _e == "persona":
        _r["signum"] = _fmt_num(_digits(300, _r["idx"] + 1))
    elif _e == "sl":
        _r["signum"] = _fmt_num(_digits(600, _r["idx"] + 1))
    else:
        _f = _r["field"]
        _per_field[_f] = _per_field.get(_f, 0) + 1
        _r["signum"] = _fmt_num(_digits(_FIELD_DIST[_f], _per_field[_f]))

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
    import gzip
    # curl, not urllib: python urllib hangs through this sandbox's egress proxy
    # (AGENTS.md), curl works. Same fallback semantics as before.
    curl = subprocess.run(
        ["curl", "-sL", "--max-time", "90", "-A", "JAH-QA-build-catalog/1.0",
         "https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz"],
        capture_output=True, timeout=100)
    if curl.returncode != 0 or not curl.stdout:
        raise RuntimeError("curl fetch failed (rc=%s)" % curl.returncode)
    idx = json.loads(gzip.decompress(curl.stdout).decode("utf-8"))
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
    elif r["embed"] == "sl":
        typ, role, file_id = "sl", "SIGNATURE-LINE", o["id"]
    else:
        typ, role, file_id = "domain", "ASSISTANT", o["id"]
    abilities = o.get("abilities") or []
    desc = o.get("mentality", "")
    rel = {}
    if r["embed"] == "persona":
        rel["disclaimer"] = "fan-style simulation, not affiliated with any rights holder"
    if r["embed"] == "sl":
        m = o.get("mirror") or {}
        rel["disclaimer"] = "independent interpretation; not affiliated with the vendor"
        rel["mirrors"] = {"model": m.get("model", ""), "vendor": m.get("vendor", ""),
                          "url": m.get("url", ""), "original_status": m.get("status", "")}
    if r["embed"] == "domain":
        rel["domain"] = o.get("domain", "")
        rel["demo_kind"] = o.get("demoKind", "")
    canon = json.dumps([stamp, o["name"], typ, desc, abilities], sort_keys=True)
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    pro = bool(o.get("pro"))
    limit = ("Chat answers are persona-driven, generated by a small on-device model — "
             "verify important facts elsewhere.")
    if pro:
        limit += " Gives general information only; not a licensed professional."
    if r["embed"] == "persona":
        limit += " Fan-style fiction simulation, not the real character."
    if r["embed"] == "sl":
        limit += (" Signature-Line twin: original Signature-math implementation; "
                  "capability claims mirror the vendor's published claims.")
    records.append({
        "ID": stamp,
        "NAME": o["name"],
        "TYPE": typ,
        "CATEGORY": o.get("domain") or {"system": "System", "persona": "Persona",
                                        "sl": "Signature-Line"}.get(typ, "Domain"),
        "DESCRIPTION": desc,
        "CAPABILITIES": abilities,
        "LIMITATIONS": limit,
        "STATUS": "PUBLISHED",
        "VERSION": o.get("ver", "1.0"),
        "ROLE": role,
        "RUNTIME": {
            "what_you_download": "Python/JS source file (human-readable, runs locally) — logic and persona code, not trained-model weights",
            "what_the_demo_is": "the same logic running live in the page's JavaScript (website demo, not the full runtime)",
            "what_the_chat_is": "generated on-device by Signature Llama v2 when weights load; otherwise the JAHtalk basic-LLM engine — every reply says which answered",
            "works_offline": "YES — after the page loads",
            "internet_required": "NO for demos/downloads; YES once to fetch the page and chat weights",
            "browser_only": "NO — downloads run anywhere with Python 3; the chat demo runs in the browser",
            "local_download": "YES",
        },
        "DEMO": {"kind": o.get("demoKind", ""), "runs_in": "browser", "url": SITE + "#file-" + file_id},
        "VOICE": {"read_aloud": True, "engine": "browser speech synthesis (tiered TTS)"},
        "SIGNATURE_NUMBER": r["signum"],
        "SOURCE": ("embedded in js/sl_twins.js — Signature-made by Justin Addam Higgins"
                   if r["embed"] == "sl" else
                   "embedded in index.html — Signature-made by Justin Addam Higgins"),
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
        "sl": sum(1 for x in records if x["TYPE"] == "sl"),
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
                                "domain": counts["domain"],
                                "sl": counts.get("sl", 0)},
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
                                   "domain": counts["domain"],
                                   "sl": counts.get("sl", 0)},
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
         "desc": "Machine-readable catalog of the %d embedded AI files, one AI File Standard record each: ID/NAME/TYPE/CATEGORY/DESCRIPTION/CAPABILITIES/LIMITATIONS/STATUS/VERSION/ROLE/RUNTIME/DEMO/VOICE/SIGNATURE_NUMBER/SOURCE/RELATIONSHIPS/HASH/ARTIFACTS." % counts["embedded_total"]},
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
new_break = ('PUBLISHED AI FILES: <b>%s</b> = %d embedded (%d system &middot; %d persona &middot; %d domain &middot; %d signature-line) '
             '+ %s word-AIs &middot; Last synchronized %s &mdash; live count refreshes when the word-AI index loads'
             % (format(pub, ",d"), emb, counts["system"], counts["persona"], counts["domain"],
                counts.get("sl", 0),
                format(wa, ",d"), asof))
hero = re.sub(r'<span id="aibreakdown">.*?</span>',
              '<span id="aibreakdown">' + new_break + '</span>', hero, count=1, flags=re.S)
open(hero_path, "w", encoding="utf-8").write(hero)
print("stamped hero: %s published (%d embedded + %d word-AIs), as of %s"
      % (format(pub, ",d"), emb, wa, asof))

# ---- stamp the other crawler-visible count statements from the same source ----
hero = open(hero_path, encoding="utf-8").read()
hero = re.sub(
    r'<meta name="description" content="The Signature AI Phone Book[^"]*">',
    '<meta name="description" content="The Signature AI Phone Book — home of every AI. '
    'Dial %s+ published AI files: %d Signature system AIs, %d persona AIs, %d domain AIs for every need in life, '
    '%d Signature-Line twins of market AIs, '
    'and %s word AIs — each with dossier, working demo, dialog, read-aloud, copy and download. '
    'Counts last synchronized %s.">'
    % (format(pub, ",d"), counts["system"], counts["persona"], counts["domain"],
       counts.get("sl", 0), format(wa, ",d"), asof),
    hero, count=1)
hero = re.sub(
    r'"description": "Published AI files: 22,460 = 260 embedded[^"]*"',
    '"description": "Published AI files: %s = %d embedded (%d system, %d persona, %d domain, %d signature-line) + %s word AIs. '
    'Counts last synchronized %s; the page\'s live counter refreshes from the word-AI index at '
    'https://justinahiggins614-cmyk.github.io/signature-one-archive/data/index/wordai.idx.json.gz. '
    'Per-AI machine records: ai-catalog.json."'
    % (format(pub, ",d"), emb, counts["system"], counts["persona"], counts["domain"],
       counts.get("sl", 0), format(wa, ",d"), asof),
    hero, count=1)
hero = re.sub(
    r'\(all [\d,]+ embedded AI files, machine-readable\)',
    '(all %d embedded AI files, machine-readable)' % emb, hero, count=1)
hero = re.sub(
    r'\(\d[\d,]* word AIs as of \d{4}-\d{2}-\d{2}',
    '(%s word AIs, last synchronized %s' % (format(wa, ",d"), asof), hero, count=1)
open(hero_path, "w", encoding="utf-8").write(hero)
print("stamped meta/JSON-LD/crawler note")

# ---- rebuild archive.html from the JUST-WRITTEN catalog (never one run behind) ----
# Hook: this runs AFTER ai-catalog.json + api.json + hero stamps are flushed above,
# so the archive's count header and letter lists always match the current data.
try:
    import build_archive
    build_archive.build()
except ImportError:
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        "build_archive", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_archive.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build()
