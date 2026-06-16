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

## v0.2-local Scope

- Ignored local inventory runtime under `inventory/`.
- Sanitized local inventory templates in `examples/`.
- `scripts/init-local-inventory.sh` for creating local inventory files without overwriting existing files.
- `scripts/validate-inventory.py` for standard-library validation of local device and service JSON.
- Doctor integration for inventory validation, script syntax checks, security scanning, and repository status review.

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

To initialize ignored local inventory files, run:

```bash
bash scripts/init-local-inventory.sh
```

To validate local inventory at any time, run:

```bash
python3 scripts/validate-inventory.py
```

See `docs/V0_2_LOCAL_INVENTORY_RUNTIME.md` for the local runtime rules and limitations.

## No Secrets Policy

Do not commit secrets or sensitive operational data. Public examples must be fake or sanitized. Treat this repository as shareable by default, even if it remains private.

## Future Console Integration

Future versions may expose the sanitized schemas and local data layout to HALO Console as a read-only source of inventory, services, and runbook metadata. That integration should preserve the boundary between this repository as the private control-plane foundation and the console as a separate application experience.
