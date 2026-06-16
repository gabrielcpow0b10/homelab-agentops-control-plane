#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "init-local-inventory: creating ignored local inventory directory"
mkdir -p inventory

if [ ! -f inventory/devices.local.json ]; then
  cp examples/inventory.local.example.json inventory/devices.local.json
  echo "init-local-inventory: created inventory/devices.local.json"
else
  echo "init-local-inventory: inventory/devices.local.json already exists; not overwriting"
fi

if [ ! -f inventory/services.local.json ]; then
  cp examples/services.local.example.json inventory/services.local.json
  echo "init-local-inventory: created inventory/services.local.json"
else
  echo "init-local-inventory: inventory/services.local.json already exists; not overwriting"
fi

echo "init-local-inventory: inventory/ is ignored by Git"
echo "init-local-inventory: do not store passwords, tokens, keys, private paths, or real secrets"

python3 scripts/validate-inventory.py
