# HomeLab Control Plane

HomeLab Control Plane is a public, sanitized prototype for documenting and organizing a HomeLab-style control plane. It demonstrates local-first inventory modeling, safe summaries, quality gates, agent command validation, default-deny policy evaluation, redacted audit logging, and redacted approval ledger records without exposing operational HomeLab data.

This repository is separate from `halo-local-ai-console` because it is not a user interface. The console can evolve as an application layer, while this repository stays focused on durable control-plane data structures, examples, documentation, and safety checks.

This public repository is not the private operational HomeLab deployment. It contains fake examples, schemas, scripts, and documentation only.

## Public Safety Boundary

This repository is designed to be public-safe:

- No real inventory is included.
- No real policies are included.
- No runtime logs are included.
- No real device names, hosts, IPs, private paths, URLs, tokens, or secrets are included.
- Examples are fake, generic, and safe for portfolio review.
- Ignored local runtime directories are documented only as patterns for a private deployment.

See `docs/PUBLIC_SAFETY_BOUNDARY.md` for the full public safety boundary.

## Technical Architecture

- Inventory: sanitized device and service examples with JSON schemas.
- Safe Summary: redacted, count-based inventory reporting.
- Inventory Quality Gate: PASS, WARN, and FAIL checks for inventory hygiene.
- Agent Command Contract: allowlisted command request validation for future agents.
- Agent Policy Engine: default-deny policy evaluation before any execution layer.
- Agent Audit Log: redacted audit events with hashes and classifications only.
- Agent Approval Ledger: redacted approval decisions for future gated execution workflows.
- Agent Capability Registry: generic future agent class capabilities with no real deployment details.

## Portfolio Value

This project demonstrates:

- Local-first architecture for HomeLab control-plane data.
- Safe AI-to-agent command validation.
- Default-deny policy evaluation.
- Redacted audit logging.
- Redacted approval decision records.
- Public-safe capability registry validation.
- Bash and Python standard-library tooling.
- Security scanning and doctor checks for public-safe repository hygiene.

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

## v0.6-local Scope

- Safe local Agent Policy Engine for default-deny policy evaluation.
- Redacted policy reports that never execute commands or contact agents.
- Optional ignored runtime report at `runtime/agent-policy-evaluation.local.md`.
- Doctor integration for policy engine syntax and no-write evaluation.

## v0.7-local Scope

- Safe local Agent Audit Log for redacted policy evaluation events.
- SHA-256 based short hashes for request, target, policy, command, and policy references.
- Runtime audit JSONL and Markdown summary output only when explicitly requested.
- Ignored runtime audit files under `runtime/`.
- Doctor integration for audit script syntax and no-write audit generation.

## v0.8-local Scope

- Safe local Agent Approval Ledger for redacted human/operator approval decisions.
- Approval decisions for `approved`, `denied`, and `expired` outcomes.
- Authorization rules that keep denied policy results, denied approvals, and expired approvals from authorizing execution.
- Runtime approval JSONL and Markdown summary output only when explicitly requested.
- Ignored runtime approval files under `runtime/`.
- Doctor integration for approval script syntax and no-write approval generation.

## v0.9-local Scope

- Safe local Agent Capability Registry for generic future agent classes.
- Public-safe capability examples for Raspberry Pi, Mac mini, and Linux worker classes.
- Validation that checks supported action, mode, risk level, denied actions, and approval-required capability flags.
- Optional ignored runtime report at `runtime/agent-capability-summary.local.md`.
- Doctor integration for capability registry syntax and no-write validation.

## Intentionally Not Included

- Real device inventory.
- Real network addresses.
- Real hostnames.
- Real policies.
- Runtime logs.
- Real device names.
- Real hosts, IPs, private paths, or URLs.
- Passwords, tokens, keys, private keys, or `.env` content.
- Screenshots, uploaded documents, logs, PDFs, or private files.
- Cloud provider configuration.
- Application UI code.
- Network scanning.
- Remote automation.

## Local-First Design

The prototype should be useful without depending on external services. Public repository files should contain only documentation, schemas, scripts, and fake examples. In a private operational deployment, real inventory would belong in ignored local directories such as `private/`, `local/`, `inventory/`, `runtime/`, or `secrets/`.

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

To evaluate the safe example command against the safe local policy without writing a report, run:

```bash
python3 scripts/evaluate-agent-policy.py
```

To validate the safe policy flow and write the ignored policy report, run:

```bash
bash scripts/check-agent-policy.sh
```

To generate a safe redacted agent audit event without writing runtime files, run:

```bash
python3 scripts/record-agent-audit.py
```

To validate the safe audit flow and write ignored audit runtime files, run:

```bash
bash scripts/check-agent-audit.sh
```

To generate a safe redacted agent approval event without writing runtime files, run:

```bash
python3 scripts/record-agent-approval.py
```

To validate the safe approval flow and write ignored approval runtime files, run:

```bash
bash scripts/check-agent-approval.sh
```

To validate the safe capability registry without writing a report, run:

```bash
python3 scripts/validate-agent-capability.py
```

To validate the safe capability flow and write the ignored capability summary, run:

```bash
bash scripts/check-agent-capability.sh
```

See `docs/PUBLIC_SAFETY_BOUNDARY.md`, `docs/V0_2_LOCAL_INVENTORY_RUNTIME.md`, `docs/V0_3_SAFE_INVENTORY_SUMMARY.md`, `docs/V0_4_INVENTORY_QUALITY_GATE.md`, `docs/V0_5_AGENT_COMMAND_CONTRACT.md`, `docs/V0_6_AGENT_POLICY_ENGINE.md`, `docs/V0_7_AGENT_AUDIT_LOG.md`, `docs/V0_8_AGENT_APPROVAL_LEDGER.md`, and `docs/V0_9_AGENT_CAPABILITY_REGISTRY.md` for the public safety boundary, local runtime rules, reporting rules, quality gate behavior, command contract validation, policy evaluation, audit logging, approval ledger behavior, capability registry validation, and limitations.

## No Secrets Policy

Do not commit secrets or sensitive operational data. Public examples must be fake and sanitized. Treat this repository as shareable by default.

## Future Console Integration

Future versions may expose the sanitized schemas and local data layout to HALO Console as a read-only source of fake inventory, services, and runbook metadata. A private operational deployment would keep any real data outside this public repository.

## v0.6-local Agent Policy Engine

v0.6-local adds a safe local Agent Policy Engine. It evaluates validated Agent Command Contract requests against local default-deny policy rules before any future agent execution layer exists.

The engine never executes commands, contacts agents, or calls network services. Normal output is redacted and count-based.

```bash
python3 scripts/evaluate-agent-policy.py
bash scripts/check-agent-policy.sh
```

## v0.7-local Agent Audit Log

v0.7-local adds a safe local Agent Audit Log. It records one redacted policy evaluation event with hashes and classifications only.

The audit script never executes commands, contacts agents, or calls network services. Default mode does not write runtime files.

```bash
python3 scripts/record-agent-audit.py
bash scripts/check-agent-audit.sh
```

## v0.8-local Agent Approval Ledger

v0.8-local adds a safe local Agent Approval Ledger. It records a redacted approval decision after command validation and policy evaluation, using hashes and classifications only.

The approval script never executes commands, contacts agents, or calls network services. Default mode does not write runtime files.

```bash
python3 scripts/record-agent-approval.py
bash scripts/check-agent-approval.sh
```

## v0.9-local Agent Capability Registry

v0.9-local adds a safe local Agent Capability Registry. It validates generic future agent classes and checks whether a validated command action has a matching enabled capability.

The capability script never executes commands, contacts agents, or calls network services. Default mode does not write runtime files.

```bash
python3 scripts/validate-agent-capability.py
bash scripts/check-agent-capability.sh
```
