#!/bin/bash
# Nightly consistency gate for the Signature AI Phone Book.
# Runs every QA checker; exits 1 (and prints FAILURES) if anything disagrees.
# Fix-list items 227-234: homepage count <-> JSON <-> API <-> word-AI index <->
# sitemap must agree; duplicate IDs, missing IDs, broken deep links fail loudly.
#
# To schedule (needs Manon's word): a nightly cron running this script and
# paging only on non-zero exit.
set -u
cd "$(dirname "$0")/../.." || exit 1
FAIL=0
run() {
  echo "=== $1 ==="
  if ! python3 "$1"; then FAIL=1; echo "!!! FAILED: $1"; fi
  echo
}
run code/qa/count_check.py
run code/qa/dup_id_check.py
run code/qa/missing_id_check.py
run code/qa/check_sitemap.py
if [ "$FAIL" -ne 0 ]; then
  echo "NIGHTLY GATE: FAILURES PRESENT"
  exit 1
fi
echo "NIGHTLY GATE: ALL CLEAN"
