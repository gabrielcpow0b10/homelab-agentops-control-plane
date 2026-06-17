#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

policy_file="examples/agent-policy.local.example.json"
command_file="examples/agent-command.health-check.example.json"
runtime_report="runtime/agent-policy-evaluation.local.md"

python3 scripts/evaluate-agent-policy.py "$policy_file" "$command_file"
python3 scripts/evaluate-agent-policy.py --write-runtime-report "$policy_file" "$command_file"

if ! git check-ignore -q "$runtime_report"; then
  echo "agent policy runtime report is not ignored by Git"
  exit 1
fi

if git diff --cached --quiet; then
  :
else
  echo "staged changes detected after policy check"
  exit 1
fi

echo "Agent policy check completed without staging, committing, pushing, or publishing."
