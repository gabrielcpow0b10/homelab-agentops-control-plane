#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

policy_file="examples/agent-policy.local.example.json"
command_file="examples/agent-command.health-check.example.json"
runtime_log="runtime/agent-audit.local.jsonl"
runtime_summary="runtime/agent-audit-summary.local.md"

echo "check-agent-audit: generating safe redacted audit event without runtime writes"
python3 scripts/record-agent-audit.py "$policy_file" "$command_file"

echo "check-agent-audit: writing ignored runtime audit files"
python3 scripts/record-agent-audit.py --append-runtime-log --write-runtime-summary "$policy_file" "$command_file"

if git check-ignore -q "$runtime_log" 2>/dev/null; then
  echo "check-agent-audit: runtime audit log is ignored by Git"
else
  echo "check-agent-audit: runtime audit log is not ignored by Git"
  exit 1
fi

if git check-ignore -q "$runtime_summary" 2>/dev/null; then
  echo "check-agent-audit: runtime audit summary is ignored by Git"
else
  echo "check-agent-audit: runtime audit summary is not ignored by Git"
  exit 1
fi

if git diff --cached --quiet; then
  :
else
  echo "check-agent-audit: staged changes detected"
  exit 1
fi

echo "check-agent-audit: no files were staged, committed, pushed, or published"
