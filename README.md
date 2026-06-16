# HomeLab Control Plane

HomeLab Control Plane is a private, local-first foundation for documenting and organizing a personal lab environment. It is intended to hold sanitized inventory models, service metadata, runbook references, and security boundary notes that can later be consumed by other local tools.

This repository is separate from `halo-local-ai-console` because it is not a user interface. The console can evolve as an application layer, while this repository stays focused on durable control-plane data structures, examples, documentation, and safety checks.

## v0.1 Scope

- Sanitized device inventory examples.
- Sanitized service inventory examples.
- Runbook reference examples.
- JSON schemas for devices and services.
- Security boundaries and documentation rules.
- Local validation scripts for syntax checks and conservative secret-pattern scanning.

## Intentionally Not Included

- Real device inventory.
- Real network addresses.
- Real hostnames.
- Passwords, tokens, keys, private keys, or `.env` content.
- Screenshots, uploaded documents, logs, PDFs, or private files.
- Cloud provider configuration.
- Application UI code.
- Network scanning.
- Remote automation.

## Local-First Design

The control plane should be useful without depending on external services. Public repository files should contain only documentation, schemas, scripts, and fake examples. Real inventory belongs in ignored local directories such as `private/`, `local/`, `inventory/`, `runtime/`, or `secrets/`.

## No Secrets Policy

Do not commit secrets or sensitive operational data. Public examples must be fake or sanitized. Treat this repository as shareable by default, even if it remains private.

## Future Console Integration

Future versions may expose the sanitized schemas and local data layout to HALO Console as a read-only source of inventory, services, and runbook metadata. That integration should preserve the boundary between this repository as the private control-plane foundation and the console as a separate application experience.
