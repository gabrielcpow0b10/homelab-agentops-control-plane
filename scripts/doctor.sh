#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "doctor: repository"
git status --short

echo "doctor: bash syntax"
bash -n scripts/security-scan.sh
bash -n scripts/doctor.sh

echo "doctor: security scan"
bash scripts/security-scan.sh

echo "doctor: git status"
git status --short

echo "doctor: passed"
