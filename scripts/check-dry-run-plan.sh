#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

REGISTRY="examples/agent-capability.local.example.json"
POLICY="examples/agent-policy.local.example.json"
HEALTH_COMMAND="examples/agent-command.health-check.example.json"
APPROVAL_COMMAND="examples/agent-command.restart-service.requires-approval.example.json"
RUNTIME_PLAN="runtime/agent-dry-run-plan.local.json"
RUNTIME_SUMMARY="runtime/agent-dry-run-plan-summary.local.md"

echo "check-dry-run-plan: running safe defaults"
python3 scripts/render-dry-run-plan.py

echo "check-dry-run-plan: running explicit safe read-only inputs"
python3 scripts/render-dry-run-plan.py "$REGISTRY" "$POLICY" "$HEALTH_COMMAND"

echo "check-dry-run-plan: running approved approval-required dry-run plan"
python3 scripts/render-dry-run-plan.py "$REGISTRY" "$POLICY" "$APPROVAL_COMMAND" --approval-decision approved

echo "check-dry-run-plan: writing ignored runtime dry-run files"
python3 scripts/render-dry-run-plan.py --write-runtime-plan --write-runtime-summary

if git check-ignore -q "$RUNTIME_PLAN" 2>/dev/null; then
  echo "check-dry-run-plan: runtime plan is ignored by Git"
else
  echo "check-dry-run-plan: runtime plan is not ignored by Git"
  exit 1
fi

if git check-ignore -q "$RUNTIME_SUMMARY" 2>/dev/null; then
  echo "check-dry-run-plan: runtime summary is ignored by Git"
else
  echo "check-dry-run-plan: runtime summary is not ignored by Git"
  exit 1
fi

if ! git diff --cached --quiet; then
  echo "check-dry-run-plan: staged changes detected"
  exit 1
fi

echo "check-dry-run-plan: no files were staged, committed, pushed, or published"
