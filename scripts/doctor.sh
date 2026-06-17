#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/halo-homelab-control-plane-pycache}"

echo "doctor: repository"
git status --short

echo "doctor: bash syntax"
bash -n scripts/security-scan.sh
bash -n scripts/doctor.sh
bash -n scripts/init-local-inventory.sh
bash -n scripts/report-inventory.sh
bash -n scripts/check-inventory-quality.sh
bash -n scripts/check-agent-command.sh
bash -n scripts/check-agent-policy.sh

echo "doctor: python syntax"
python3 -m py_compile scripts/validate-inventory.py
python3 -m py_compile scripts/summarize-inventory.py
python3 -m py_compile scripts/check-inventory-quality.py
python3 -m py_compile scripts/validate-agent-command.py
python3 -m py_compile scripts/evaluate-agent-policy.py

echo "doctor: local inventory validation"
python3 scripts/validate-inventory.py

echo "doctor: safe inventory summary"
python3 scripts/summarize-inventory.py

echo "doctor: inventory quality gate"
python3 scripts/check-inventory-quality.py

echo "doctor: agent command contract"
python3 scripts/validate-agent-command.py

echo "doctor: agent policy engine"
python3 scripts/evaluate-agent-policy.py

echo "doctor: security scan"
bash scripts/security-scan.sh

echo "doctor: git status"
git status --short

echo "doctor: passed"
