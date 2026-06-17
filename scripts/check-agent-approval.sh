#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

policy_file="examples/agent-policy.local.example.json"
command_file="examples/agent-command.restart-service.requires-approval.example.json"
runtime_ledger="runtime/agent-approval-ledger.local.jsonl"
runtime_summary="runtime/agent-approval-summary.local.md"

echo "check-agent-approval: generating safe redacted approval event without runtime writes"
python3 scripts/record-agent-approval.py "$policy_file" "$command_file" approved

echo "check-agent-approval: writing ignored runtime approval files"
python3 scripts/record-agent-approval.py --append-runtime-ledger --write-runtime-summary "$policy_file" "$command_file" approved

if git check-ignore -q "$runtime_ledger" 2>/dev/null; then
  echo "check-agent-approval: runtime approval ledger is ignored by Git"
else
  echo "check-agent-approval: runtime approval ledger is not ignored by Git"
  exit 1
fi

if git check-ignore -q "$runtime_summary" 2>/dev/null; then
  echo "check-agent-approval: runtime approval summary is ignored by Git"
else
  echo "check-agent-approval: runtime approval summary is not ignored by Git"
  exit 1
fi

if git diff --cached --quiet; then
  :
else
  echo "check-agent-approval: staged changes detected"
  exit 1
fi

echo "check-agent-approval: no files were staged, committed, pushed, or published"
