#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

EXAMPLES=(
  "examples/agent-command.health-check.example.json"
  "examples/agent-command.backup-dry-run.example.json"
  "examples/agent-command.restart-service.requires-approval.example.json"
)

echo "check-agent-command: validating safe example command contracts"
python3 scripts/validate-agent-command.py "${EXAMPLES[@]}"

echo "check-agent-command: writing ignored safe command contract report"
python3 scripts/validate-agent-command.py --write-runtime-report "${EXAMPLES[@]}"

if [ -f runtime/agent-command-contract.local.md ]; then
  echo "check-agent-command: wrote runtime/agent-command-contract.local.md"
else
  echo "check-agent-command: runtime/agent-command-contract.local.md was not written"
  exit 1
fi

if git check-ignore -q runtime/agent-command-contract.local.md 2>/dev/null; then
  echo "check-agent-command: runtime/agent-command-contract.local.md is ignored by Git"
else
  echo "check-agent-command: runtime/agent-command-contract.local.md is not ignored by Git"
  exit 1
fi

echo "check-agent-command: no files were staged, committed, pushed, or published"
