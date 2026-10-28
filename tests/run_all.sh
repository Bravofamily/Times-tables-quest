#!/bin/bash
# Runs every browser test against ../index.html. Needs Python 3 + Playwright (chromium and webkit).
cd "$(dirname "$0")"; fail=0
for t in test_*.py; do python3 -u "$t" > "${t%.py}.log" 2>&1 || { echo "FAIL $t"; fail=1; }; done
[ $fail = 0 ] && echo "ALL PASS"; exit $fail
