#!/usr/bin/env python3
"""Sitemap-liveness checker for the Signature AI Telephone Book (jah-ai-models).

Verifies sitemap.xml is well-formed and every unique URL it contains returns
HTTP 200 from the live site:
  * XML parses and uses the sitemap 0.9 namespace
  * every <loc> is an absolute https URL on the jah-ai-models site
  * the embedded AI deep links (index.html#file-<id>) match the AI ids
  *   actually embedded in index.html — no orphans, none missing (count derived,
  *   never hardcoded)
    actually embedded in index.html — no orphans, none missing
  * key pages present: index.html, canonical home, ai-catalog.json, api.json,
    and the wing anchors (#thebook A-Z, #sisterlines, #genomelab, #arena,
    #mixlab, #incoming, #llamashow)
  * every unique URL (fragment stripped) returns HTTP 200 via GET

Word-AI pages are deliberately NOT listed here: they live in the
signature-one-archive repo (see the sitemap's XML comment). Their index is
checked by updateBookstats' fetch, not duplicated here.

Re-runnable:  python3 code/qa/check_sitemap.py
Exit code 0 = clean, 1 = problems found.
"""
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SITEMAP = os.path.join(REPO, "sitemap.xml")
HTML = os.path.join(REPO, "index.html")
BASE = "https://justinahiggins614-cmyk.github.io/jah-ai-models/"

problems = []


def curl_status(url):
    """GET via curl (per AGENTS.md: curl works through the egress proxy)."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "40", "-A", "JAH-QA-sitemap-check/1.0", url],
            capture_output=True, text=True, timeout=50)
        return r.stdout.strip() or "curl-empty"
    except Exception as e:  # noqa: BLE001 - report, don't trace
        return "ERROR: %s" % e


def main():
    xml_text = open(SITEMAP, encoding="utf-8").read()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print("XML PARSE ERROR:", e)
        sys.exit(1)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag != ns + "urlset":
        problems.append("root element is %s, want sitemap urlset" % root.tag)

    locs = [el.text.strip() for el in root.findall(ns + "url/" + ns + "loc")]
    print("sitemap urls:", len(locs))

    # ---- 1. all locs are absolute https on our site -----------------------
    for loc in locs:
        if not loc.startswith(BASE):
            problems.append("NON-SITE LOC: %s" % loc)

    # ---- 2. embedded AI ids match index.html --------------------------------
    html = open(HTML, encoding="utf-8").read()
    start = html.index("var SIG_AIS")
    end = html.index("function domainParams")
    twin_src = open(os.path.join(REPO, "js", "sl_twins.js"), encoding="utf-8").read()
    js = twin_src + "\n" + html[start:end] + """
var out=[];
SIG_AIS.forEach(function(a){out.push(a.id)});
PERSONAS.forEach(function(a){out.push(a.id)});
SL_TWINS.forEach(function(a){out.push(a.id)});
Object.keys(domIndex).forEach(function(k){out.push(domIndex[k].id)});
console.log(JSON.stringify(out));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tf:
        tf.write(js)
        tf_path = tf.name
    node = subprocess.run(["node", tf_path], capture_output=True, text=True)
    os.unlink(tf_path)
    if node.returncode != 0:
        sys.exit("node parse failed:\n" + node.stderr)
    import json
    embedded = json.loads(node.stdout)
    print("embedded AI ids:", len(embedded))

    sm_files = sorted(set(l[len(BASE + "index.html#file-"):]
                          for l in locs
                          if l.startswith(BASE + "index.html#file-")))
    expect = sorted(set(embedded))
    missing = [i for i in expect if i not in sm_files]
    extra = [i for i in sm_files if i not in expect]
    if missing:
        problems.append("SITEMAP MISSING %d embedded AI ids (e.g. %s)" % (len(missing), missing[:3]))
    if extra:
        problems.append("SITEMAP LISTS %d ids not embedded in page (e.g. %s)" % (len(extra), extra[:3]))
    print("embedded AI deep links in sitemap:", len(sm_files),
          "OK" if not missing and not extra else "MISMATCH")

    # ---- 3. key pages present -----------------------------------------------
    for key, label in [(BASE + "index.html", "index.html"),
                       (BASE, "canonical home"),
                       (BASE + "ai-catalog.json", "ai-catalog.json"),
                       (BASE + "api.json", "api.json"),
                       (BASE + "index.html#thebook", "A-Z book anchor"),
                       (BASE + "index.html#sisterlines", "sister-lines anchor"),
                       (BASE + "index.html#genomelab", "genome-lab anchor"),
                       (BASE + "index.html#arena", "arena anchor"),
                       (BASE + "index.html#mixlab", "mix-lab anchor"),
                       (BASE + "index.html#incoming", "incoming anchor"),
                       (BASE + "index.html#llamashow", "llama showcase anchor")]:
        ok = key in locs
        print("  %-22s %s" % (label, "OK" if ok else "MISSING"))
        if not ok:
            problems.append("SITEMAP MISSING KEY PAGE: " + label)

    # ---- 4. every unique URL (fragment stripped) returns 200 ----------------
    unique = sorted(set(l.split("#")[0] for l in locs))
    print("unique fetch URLs:", len(unique))
    for u in unique:
        st = curl_status(u)
        ok = (st == "200")
        print("  %s -> %s %s" % (u, st, "OK" if ok else "FAIL"))
        if not ok:
            problems.append("NON-200: %s -> %s" % (u, st))

    print()
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("SITEMAP CLEAN — %d urls, all 200, all %d embedded AI deep links covered" % (len(locs), len(embedded)))


if __name__ == "__main__":
    main()
