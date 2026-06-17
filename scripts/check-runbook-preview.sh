#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

REGISTRY="examples/agent-capability.local.example.json"
POLICY="examples/agent-policy.local.example.json"
HEALTH_COMMAND="examples/agent-command.health-check.example.json"
APPROVAL_COMMAND="examples/agent-command.restart-service.requires-approval.example.json"
RUNTIME_PREVIEW="runtime/agent-runbook-preview.local.json"
RUNTIME_SUMMARY="runtime/agent-runbook-preview-summary.local.md"

echo "check-runbook-preview: running safe defaults"
python3 scripts/render-runbook-preview.py

echo "check-runbook-preview: running explicit safe read-only inputs"
python3 scripts/render-runbook-preview.py "$REGISTRY" "$POLICY" "$HEALTH_COMMAND"

echo "check-runbook-preview: running approved approval-required runbook preview"
python3 scripts/render-runbook-preview.py "$REGISTRY" "$POLICY" "$APPROVAL_COMMAND" --approval-decision approved

echo "check-runbook-preview: writing ignored runtime runbook preview files"
python3 scripts/render-runbook-preview.py --write-runtime-preview --write-runtime-summary

if git check-ignore -q "$RUNTIME_PREVIEW" 2>/dev/null; then
  echo "check-runbook-preview: runtime preview is ignored by Git"
else
  echo "check-runbook-preview: runtime preview is not ignored by Git"
  exit 1
fi

if git check-ignore -q "$RUNTIME_SUMMARY" 2>/dev/null; then
  echo "check-runbook-preview: runtime summary is ignored by Git"
else
  echo "check-runbook-preview: runtime summary is not ignored by Git"
  exit 1
fi

if ! git diff --cached --quiet; then
  echo "check-runbook-preview: staged changes detected"
  exit 1
fi

echo "check-runbook-preview: no files were staged, committed, pushed, or published"
