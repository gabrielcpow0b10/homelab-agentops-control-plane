#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "report-inventory: validating local inventory"
python3 scripts/validate-inventory.py

echo "report-inventory: writing ignored safe summary report"
python3 scripts/summarize-inventory.py --write-runtime-report

if [ -f runtime/inventory-summary.local.md ]; then
  echo "report-inventory: wrote runtime/inventory-summary.local.md"
else
  echo "report-inventory: no report written because no local inventory JSON files were found"
fi

if git check-ignore -q runtime/inventory-summary.local.md 2>/dev/null; then
  echo "report-inventory: runtime/ is ignored by Git"
else
  echo "report-inventory: runtime/ is not ignored by Git"
  exit 1
fi

echo "report-inventory: no files were staged, committed, pushed, or published"
