#!/bin/bash
# Run every suite one at a time. usage: tests/run_all.sh chromium|webkit [site-dir]
# Site dir defaults to the repo root; pass a scratch copy to keep screenshots out of the repo.
B=${1:-chromium}; HERE=$(cd "$(dirname "$0")" && pwd)
export PWB=$B NR_DIR=${2:-$(dirname "$HERE")}
PY=${PY:-python3}; LOGS=${LOGS:-/tmp/numirealm-logs}; mkdir -p "$LOGS"
for t in test_game_v9 test_friends_v9 test_subjects_v9 test_about_v9 test_v10_save test_v11_hints test_v11_layout test_v12_screens test_v12_layout test_v13 test_v14 test_v15 test_v16 test_v17 test_v18 test_v19 test_v20 test_v21 test_version_v22 test_v22; do
  L="$LOGS/$B-$t.log"
  (cd "$HERE" && timeout 900 "$PY" -u $t.py > "$L" 2>&1); echo "EXIT $?" >> "$L"
  echo "$t $(tail -1 "$L")"
done
