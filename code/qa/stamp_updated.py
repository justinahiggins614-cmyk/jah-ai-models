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
    # The footer date is Manon-facing: convert to his local date (America/New_York),
    # never the VM's UTC clock (which flips to "tomorrow" hours before his day ends).
    from zoneinfo import ZoneInfo
    import datetime
    ci = out.stdout.strip()  # e.g. "2026-10-02 03:12:52 +0000"
    dt = datetime.datetime.strptime(ci, "%Y-%m-%d %H:%M:%S %z")
    date = dt.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    html = io.open(HTML, encoding="utf-8").read()
    new, n = re.subn(r'(<span id="siteupdated">)\d{4}-\d{2}-\d{2}(</span>)',
                     r"\g<1>" + date + r"\g<2>", html)
    if n != 1:
        raise SystemExit("expected exactly 1 #siteupdated span, found %d" % n)
    io.open(HTML, "w", encoding="utf-8").write(new)
    print("siteupdated stamped:", date)


if __name__ == "__main__":
    main()
