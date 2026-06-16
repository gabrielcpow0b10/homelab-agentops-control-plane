# Security Boundaries

This repository is safe-by-default documentation and metadata. It should not contain sensitive operational data.

## Allowed in Public Repo Files

- Fake examples.
- JSON schemas.
- Documentation.
- Validation scripts.
- Sanitized runbook templates.

## Not Allowed in Public Repo Files

- Real addresses.
- Real hostnames.
- Secrets, keys, tokens, or credentials.
- Private logs.
- Screenshots.
- Uploaded documents.
- PDFs.
- Real access instructions.
- Network scanning logic.
- Cloud provider configuration.

## Local-Only Files

Real inventory and operational notes should stay in ignored local directories. Keep committed files generic enough that they can be reviewed without exposing the environment.
