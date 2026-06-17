#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

REGISTRY="examples/agent-capability.local.example.json"
COMMAND="examples/agent-command.health-check.example.json"
SUMMARY="runtime/agent-capability-summary.local.md"

echo "check-agent-capability: validating safe example capability registry"
python3 scripts/validate-agent-capability.py "$REGISTRY"

echo "check-agent-capability: validating safe registry plus safe command"
python3 scripts/validate-agent-capability.py "$REGISTRY" "$COMMAND"

echo "check-agent-capability: writing ignored safe capability summary"
python3 scripts/validate-agent-capability.py --write-runtime-summary "$REGISTRY" "$COMMAND"

if [ -f "$SUMMARY" ]; then
  echo "check-agent-capability: wrote $SUMMARY"
else
  echo "check-agent-capability: $SUMMARY was not written"
  exit 1
fi

if git check-ignore -q "$SUMMARY" 2>/dev/null; then
  echo "check-agent-capability: $SUMMARY is ignored by Git"
else
  echo "check-agent-capability: $SUMMARY is not ignored by Git"
  exit 1
fi

if ! git diff --cached --quiet; then
  echo "check-agent-capability: staged changes detected"
  exit 1
fi

echo "check-agent-capability: no files were staged, committed, pushed, or published"
