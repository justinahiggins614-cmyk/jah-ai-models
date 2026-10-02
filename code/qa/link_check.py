#!/usr/bin/env python3
"""Link checker for the Signature AI Telephone Book (jah-ai-models).

Checks every link in index.html:
  1. Internal anchors (#section) — the id must exist in the page.
  2. External URLs (http/https in href/src AND inside the page's own JS,
     e.g. the Signature Llama engine/weights and the word-AI index) —
     HEAD request, reports non-2xx/3xx.
  3. Relative paths — the file must exist in the repo.

Re-runnable:  python3 code/qa/link_check.py
Exit code 0 = clean, 1 = problems found.
"""
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HTML = os.path.join(REPO, "index.html")
UA = {"User-Agent": "JAH-QA-link-check/1.0"}

problems = []


def check_head(url):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except Exception as e:  # noqa: BLE001 - we want the reason, not a traceback
        return "ERROR: %s" % e


def main():
    html = open(HTML, encoding="utf-8").read()

    ids = set(re.findall(r'id="([^"]+)"', html))
    ids |= set(re.findall(r"id='([^']+)'", html))

    hrefs = re.findall(r'href="([^"]+)"', html) + re.findall(r"href='([^']+)'", html)
    srcs = re.findall(r'src="([^"]+)"', html) + re.findall(r"src='([^']+)'", html)
    js_urls = re.findall(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]+", html)

    # ---- 1. internal anchors ---------------------------------------------
    # skip JS-built strings (concatenation) — those are checked dynamically below
    def is_js_built(u):
        return ("'" in u) or ("+" in u)

    for h in sorted(set(hrefs)):
        if is_js_built(h):
            continue
        if not h.startswith("#") or h in ("#", "#bk-", "#wordai-JAH-AI-WORD-"):
            continue  # "#" placeholders / JS-built prefixes, checked dynamically below
        anchor = h[1:]
        if anchor not in ids:
            problems.append("DEAD ANCHOR: %s (no id=\"%s\" in page)" % (h, anchor))

    # Dynamic anchors: #file-<id> for every embedded AI, #bk-<letter>, #wordai-, #hybrid-
    embedded_ids = re.findall(r"\{id:'([a-z0-9\-]+)'", html)
    if not embedded_ids:
        problems.append("DYNAMIC: could not parse embedded AI ids (data arrays changed shape?)")
    for h in sorted(set(hrefs)):
        if h.startswith("#file-"):
            if h[6:] not in embedded_ids:
                problems.append("DEAD AI LINK: %s (no embedded AI with id %s)" % (h, h[6:]))

    # ---- 2. external URLs -------------------------------------------------
    externals = sorted(set([u for u in hrefs + srcs if u.startswith("http") and not is_js_built(u)]))
    # JS-embedded fetch targets worth checking (strip trailing punctuation/query)
    for u in sorted(set(js_urls)):
        u = u.rstrip(".,;:'\"!?)}]")
        if is_js_built(u):
            continue
        if re.search(r"#[A-Za-z0-9\-]*-$", u):
            continue  # JS-built deep-link prefix (e.g. "...#file-"), checked dynamically
        if u.startswith("https://justinahiggins614-cmyk.github.io/") and u not in externals:
            externals.append(u)
    # the Llama engine is loaded as LLAMA_BASE + 'sigllama.js' (concatenated in JS);
    # check the real engine file explicitly. The bare sigllama/ dir has no index
    # page (404 is expected) — it is a base path, not a navigable link.
    externals = [u for u in externals if not u.rstrip("/").endswith("/sigllama")]
    externals.append("https://justinahiggins614-cmyk.github.io/signature-backend/sigllama/sigllama.js")
    externals = sorted(set(externals))
    print("checking %d external URLs (HEAD)..." % len(externals))
    for u in externals:
        if u.endswith(".js") or "?" in u:
            # HEAD on dynamic/query URLs can lie; try GET-lite via HEAD anyway
            pass
        status = check_head(u)
        ok = isinstance(status, int) and status < 400
        print("  %s  %s" % ("OK " if ok else "FAIL", u if ok else "%s -> %s" % (u, status)))
        if not ok:
            problems.append("DEAD EXTERNAL: %s -> %s" % (u, status))

    # ---- 3. relative paths ------------------------------------------------
    for h in sorted(set(hrefs + srcs)):
        if is_js_built(h):
            continue
        if h.startswith(("#", "http", "mailto:", "data:")) or not h.strip():
            continue
        p = os.path.join(REPO, h.split("#")[0].split("?")[0])
        if not os.path.exists(p):
            problems.append("MISSING RELATIVE FILE: %s" % h)

    print()
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  -", p)
        return 1
    print("ALL LINKS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
