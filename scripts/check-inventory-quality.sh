#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "check-inventory-quality: validating local inventory"
python3 scripts/validate-inventory.py

echo "check-inventory-quality: writing ignored safe quality report"
python3 scripts/check-inventory-quality.py --write-runtime-report

if [ -f runtime/inventory-quality.local.md ]; then
  echo "check-inventory-quality: wrote runtime/inventory-quality.local.md"
else
  echo "check-inventory-quality: no report written because no local inventory JSON files were found"
fi

if git check-ignore -q runtime/inventory-quality.local.md 2>/dev/null; then
  echo "check-inventory-quality: runtime/inventory-quality.local.md is ignored by Git"
else
  echo "check-inventory-quality: runtime/inventory-quality.local.md is not ignored by Git"
  exit 1
fi

echo "check-inventory-quality: no files were staged, committed, pushed, or published"
