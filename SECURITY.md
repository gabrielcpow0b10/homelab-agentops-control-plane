# Security Policy

This repository is designed to remain safe as a public sanitized prototype for HomeLab-style documentation and metadata.

## Rules

- Never commit `.env` files or `.env` variants.
- Never commit private IP addresses unless they have been intentionally sanitized.
- Never commit passwords, tokens, API keys, SSH keys, private keys, or other secrets.
- Never commit screenshots, uploaded private documents, private logs, or PDFs.
- Keep real inventory in ignored local files and directories.
- Keep public examples fake, generic, and sanitized.

## Local Data

In a private operational deployment, ignored directories such as `private/`, `local/`, `inventory/`, `runtime/`, and `secrets/` may hold real local records. These locations are intentionally excluded from version control by `.gitignore` and must not be populated with real data in the public portfolio snapshot.

## Review Before Sharing

Before sharing, exporting, or committing changes, run:

```bash
bash scripts/doctor.sh
```

The scanner is intentionally conservative. If it fails, inspect the matching file and sanitize the content before committing.
