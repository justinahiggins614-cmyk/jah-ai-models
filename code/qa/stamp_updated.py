#!/usr/bin/env python3
"""Stamp the "Site updated" line in index.html.

Derives the date from the most recent commit that touched the page or its
data files (ai-catalog.json, api.json) — never a hardcoded guess. Run this
right before committing a polish pass so the footer line stays honest.

Re-runnable:  python3 code/qa/stamp_updated.py
"""
import io
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HTML = os.path.join(REPO, "index.html")


def main():
    out = subprocess.run(
        ["git", "log", "-1", "--format=%ci", "--", "index.html", "ai-catalog.json", "api.json"],
        cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        raise SystemExit("could not read git log: " + out.stderr)
    date = out.stdout.strip().split(" ")[0]  # YYYY-MM-DD
    html = io.open(HTML, encoding="utf-8").read()
    new, n = re.subn(r'(<span id="siteupdated">)\d{4}-\d{2}-\d{2}(</span>)',
                     r"\g<1>" + date + r"\g<2>", html)
    if n != 1:
        raise SystemExit("expected exactly 1 #siteupdated span, found %d" % n)
    io.open(HTML, "w", encoding="utf-8").write(new)
    print("siteupdated stamped:", date)


if __name__ == "__main__":
    main()
