#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

REGISTRY="examples/agent-capability.local.example.json"
POLICY="examples/agent-policy.local.example.json"
HEALTH_COMMAND="examples/agent-command.health-check.example.json"
APPROVAL_COMMAND="examples/agent-command.restart-service.requires-approval.example.json"
RUNTIME_RESULT="runtime/agent-simulation-result.local.json"
RUNTIME_SUMMARY="runtime/agent-simulation-summary.local.md"

echo "check-readonly-agent-simulator: running safe defaults"
python3 scripts/simulate-readonly-agent.py

echo "check-readonly-agent-simulator: running explicit safe read-only inputs"
python3 scripts/simulate-readonly-agent.py "$REGISTRY" "$POLICY" "$HEALTH_COMMAND"

echo "check-readonly-agent-simulator: running approved approval-required simulation"
python3 scripts/simulate-readonly-agent.py "$REGISTRY" "$POLICY" "$APPROVAL_COMMAND" --approval-decision approved

echo "check-readonly-agent-simulator: writing ignored runtime simulation files"
python3 scripts/simulate-readonly-agent.py --write-runtime-result --write-runtime-summary

if git check-ignore -q "$RUNTIME_RESULT" 2>/dev/null; then
  echo "check-readonly-agent-simulator: runtime result is ignored by Git"
else
  echo "check-readonly-agent-simulator: runtime result is not ignored by Git"
  exit 1
fi

if git check-ignore -q "$RUNTIME_SUMMARY" 2>/dev/null; then
  echo "check-readonly-agent-simulator: runtime summary is ignored by Git"
else
  echo "check-readonly-agent-simulator: runtime summary is not ignored by Git"
  exit 1
fi

if ! git diff --cached --quiet; then
  echo "check-readonly-agent-simulator: staged changes detected"
  exit 1
fi

echo "check-readonly-agent-simulator: no files were staged, committed, pushed, or published"
