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

## v0.3-local Scope

- Safe local inventory summary generation.
- Redacted count-based reporting from ignored local inventory files.
- Optional ignored runtime report at `runtime/inventory-summary.local.md`.
- `scripts/report-inventory.sh` for validating inventory and writing the safe local report.
- Doctor integration for summary script syntax and no-write summary checks.

## v0.4-local Scope

- Safe local inventory quality gate with PASS, WARN, and FAIL results.
- Redacted quality checks for duplicate IDs, missing service owners, unknown statuses, and missing device runbooks.
- Optional ignored runtime report at `runtime/inventory-quality.local.md`.
- `scripts/check-inventory-quality.sh` for validation plus ignored quality report generation.
- Doctor integration for quality gate syntax and no-write quality checks.

## v0.5-local Scope

- Safe JSON Agent Command Contract for future HomeLab agents.
- Allowlisted actions only, with blocked arbitrary shell and sensitive access actions.
- Redacted contract validation reports with count-based PASS and FAIL output.
- Approval-required rules for future write actions.
- Optional ignored runtime report at `runtime/agent-command-contract.local.md`.
- Doctor integration for command contract syntax and no-write validation.

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

To print a safe inventory summary without writing a report, run:

```bash
python3 scripts/summarize-inventory.py
```

To validate inventory and write the ignored local report, run:

```bash
bash scripts/report-inventory.sh
```

To run the safe inventory quality gate without writing a report, run:

```bash
python3 scripts/check-inventory-quality.py
```

To validate inventory and write the ignored quality report, run:

```bash
bash scripts/check-inventory-quality.sh
```

To validate the safe agent command examples without writing a report, run:

```bash
python3 scripts/validate-agent-command.py
```

To validate the safe agent command examples and write the ignored command contract report, run:

```bash
bash scripts/check-agent-command.sh
```

See `docs/V0_2_LOCAL_INVENTORY_RUNTIME.md`, `docs/V0_3_SAFE_INVENTORY_SUMMARY.md`, `docs/V0_4_INVENTORY_QUALITY_GATE.md`, and `docs/V0_5_AGENT_COMMAND_CONTRACT.md` for the local runtime rules, reporting rules, quality gate behavior, command contract validation, and limitations.

## No Secrets Policy

Do not commit secrets or sensitive operational data. Public examples must be fake or sanitized. Treat this repository as shareable by default, even if it remains private.

## Future Console Integration

Future versions may expose the sanitized schemas and local data layout to HALO Console as a read-only source of inventory, services, and runbook metadata. That integration should preserve the boundary between this repository as the private control-plane foundation and the console as a separate application experience.

## v0.6-local Agent Policy Engine

v0.6-local adds a safe local Agent Policy Engine. It evaluates validated Agent Command Contract requests against local default-deny policy rules before any future agent execution layer exists.

The engine never executes commands, contacts agents, or calls network services. Normal output is redacted and count-based.

```bash
python3 scripts/evaluate-agent-policy.py
bash scripts/check-agent-policy.sh
```
