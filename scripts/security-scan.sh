#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

build_patterns() {
  printf '%s\n' \
    "/""Users/" \
    "~""/HomeLab" \
    "BEGIN OPENSSH PRIVATE ""KEY" \
    "BEGIN RSA PRIVATE ""KEY" \
    "sk""-" \
    "ghp""_" \
    "github_pat""_" \
    "AK""IA" \
    "password""=" \
    "token""=" \
    "api_key""=" \
    "apikey""=" \
    "secret""="
  printf '%s%s\n' "." "ssh"
}

scan_tmpdir="${TMPDIR:-/tmp}"
if [ ! -d "$scan_tmpdir" ]; then
  scan_tmpdir="/tmp"
fi

tmp_files="$(mktemp "$scan_tmpdir/halo-scan-files.XXXXXX")"
tmp_patterns="$(mktemp "$scan_tmpdir/halo-scan-patterns.XXXXXX")"
trap 'rm -f "$tmp_files" "$tmp_patterns"' EXIT

{
  git ls-files
  git ls-files --others --exclude-standard
} | sort -u > "$tmp_files"

if [ ! -s "$tmp_files" ]; then
  echo "security-scan: no public repository files to scan"
  exit 0
fi

build_patterns > "$tmp_patterns"

failures=0

while IFS= read -r file; do
  if [ ! -f "$file" ]; then
    continue
  fi

  if grep -IFn -f "$tmp_patterns" "$file" >/tmp/halo-control-plane-scan-match 2>/dev/null; then
    echo "security-scan: blocked pattern found in $file"
    cat /tmp/halo-control-plane-scan-match
    failures=1
  fi
done < "$tmp_files"

rm -f /tmp/halo-control-plane-scan-match

if [ "$failures" -ne 0 ]; then
  echo "security-scan: failed"
  exit 1
fi

echo "security-scan: passed"
