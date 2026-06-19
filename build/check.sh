#!/usr/bin/env bash
# Lightweight health check for the list-builder.
#   1. Validates every data JSON file parses (needs `jq`).
#   2. Runs the points engine over the Asuryani bundle and asserts 0 parse errors.
#   3. Flags accidental debug statements left in index.html.
# Exit non-zero if anything fails. Run from anywhere: `bash build/check.sh`.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
fail=0

echo "== 1. JSON validity =="
if command -v jq >/dev/null 2>&1; then
  count=0
  while IFS= read -r f; do
    count=$((count+1))
    if ! jq empty "$f" >/dev/null 2>&1; then
      echo "  INVALID JSON: $f"; fail=1
    fi
  done < <(find data data_* -name '*.json' 2>/dev/null)
  echo "  checked $count JSON files"
else
  echo "  (jq not installed — skipping JSON validation)"
fi

echo "== 2. Points engine =="
if [ -f app/data.js ]; then
  out=$(node build/test_engine.js 2>&1)
  echo "$out" | tail -1
  if ! echo "$out" | grep -q '; 0 errors\.'; then
    echo "  ENGINE REPORTED ERRORS"; fail=1
  fi
else
  echo "  (app/data.js not built — run build/bundle.py first; skipping)"
fi

echo "== 3. Debug leftovers in index.html =="
if grep -nE 'console\.(log|debug)|[^a-zA-Z]debugger[^a-zA-Z]' index.html; then
  echo "  found debug statements above"; fail=1
else
  echo "  none"
fi

echo
if [ "$fail" -eq 0 ]; then echo "HEALTH CHECK PASSED"; else echo "HEALTH CHECK FAILED"; fi
exit "$fail"
