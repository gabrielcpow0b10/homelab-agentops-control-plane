#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

REGISTRY="examples/agent-capability.local.example.json"
POLICY="examples/agent-policy.local.example.json"
HEALTH_COMMAND="examples/agent-command.health-check.example.json"
APPROVAL_COMMAND="examples/agent-command.restart-service.requires-approval.example.json"
RUNTIME_PACKET="runtime/agent-handoff-packet.local.json"
RUNTIME_SUMMARY="runtime/agent-handoff-packet-summary.local.md"

echo "check-handoff-packet: running safe defaults"
python3 scripts/render-handoff-packet.py

echo "check-handoff-packet: running explicit safe read-only inputs"
python3 scripts/render-handoff-packet.py "$REGISTRY" "$POLICY" "$HEALTH_COMMAND"

echo "check-handoff-packet: running approved approval-required handoff packet"
python3 scripts/render-handoff-packet.py "$REGISTRY" "$POLICY" "$APPROVAL_COMMAND" --approval-decision approved

echo "check-handoff-packet: writing ignored runtime handoff packet files"
python3 scripts/render-handoff-packet.py --write-runtime-packet --write-runtime-summary

if git check-ignore -q "$RUNTIME_PACKET" 2>/dev/null; then
  echo "check-handoff-packet: runtime packet is ignored by Git"
else
  echo "check-handoff-packet: runtime packet is not ignored by Git"
  exit 1
fi

if git check-ignore -q "$RUNTIME_SUMMARY" 2>/dev/null; then
  echo "check-handoff-packet: runtime summary is ignored by Git"
else
  echo "check-handoff-packet: runtime summary is not ignored by Git"
  exit 1
fi

if ! git diff --cached --quiet; then
  echo "check-handoff-packet: staged changes detected"
  exit 1
fi

echo "check-handoff-packet: no files were staged, committed, pushed, or published"
