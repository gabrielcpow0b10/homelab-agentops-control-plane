# HomeLab AgentOps Control Plane

A local-first AgentOps control-plane prototype for safe AI-to-agent workflow validation.

This public repository is a sanitized portfolio version of the project. It demonstrates command validation, policy evaluation, approval checks, capability matching, read-only simulation, dry-run planning, runbook preview, and handoff packet rendering without controlling real infrastructure.

It contains fake examples, schemas, scripts, and documentation only. It is not the private operational HomeLab deployment.

## What This Proves

- AI-originated requests can be reduced to a strict command contract before any agent layer exists.
- Default-deny policy checks can happen before approval, capability matching, simulation, or handoff.
- Approval state, audit records, and handoff packets can be represented with redacted hashes, counts, classifications, and booleans only.
- A local-first workflow can validate architecture, safety boundaries, and operator review steps without network contact or real execution.
- Public examples can show the engineering model without exposing real HomeLab inventory, hosts, IPs, policies, logs, credentials, or runtime artifacts.

## Current Pipeline

```text
AI request
  -> Command Contract
  -> Policy Engine
  -> Approval Ledger
  -> Capability Registry
  -> Read-only Simulator
  -> Dry-Run Plan
  -> Runbook Preview
  -> Handoff Packet
  -> No execution in public repo
```

| Layer | Purpose | Public-safe output |
| --- | --- | --- |
| Command Contract | Validate allowed request shape and action | PASS/FAIL contract report |
| Policy Engine | Apply default-deny policy before execution | Redacted policy decision |
| Approval Ledger | Record approval state for gated requests | Redacted approval event |
| Capability Registry | Match request to generic future agent class | Capability summary |
| Read-only Simulator | Combine contract, policy, approval, and capability checks | Simulated final decision |
| Dry-Run Plan | Render human-readable operational steps | Redacted dry-run plan |
| Runbook Preview | Render operator review sections | Public-safe runbook preview |
| Handoff Packet | Prepare final review or future-agent handoff | Public-safe handoff packet |

## Safety Boundary

| Boundary | Public repository rule |
| --- | --- |
| No real execution | Scripts validate, render, or simulate only. |
| No network contact | Scripts do not call remote services or scan networks. |
| No agent contact | No script contacts a real or private agent. |
| No raw HomeLab data | Real inventory, policy, logs, hosts, IPs, paths, URLs, and secrets are excluded. |
| Local runtime files ignored | Runtime and private directories are ignored for private use only. |
| Fake examples only | Tracked examples are generic and public-safe. |

See [docs/PUBLIC_SAFETY_BOUNDARY.md](docs/PUBLIC_SAFETY_BOUNDARY.md) for the full boundary.

## Milestone Index

| Milestone | Release | What it proves | Reference |
| --- | --- | --- | --- |
| v0.2 | Local Inventory Runtime | Local-only inventory can be initialized and validated outside public data. | [docs/V0_2_LOCAL_INVENTORY_RUNTIME.md](docs/V0_2_LOCAL_INVENTORY_RUNTIME.md) |
| v0.3 | Safe Inventory Summary | Inventory summaries can be redacted and count-based. | [docs/V0_3_SAFE_INVENTORY_SUMMARY.md](docs/V0_3_SAFE_INVENTORY_SUMMARY.md) |
| v0.4 | Inventory Quality Gate | Inventory hygiene can fail safely before downstream use. | [docs/V0_4_INVENTORY_QUALITY_GATE.md](docs/V0_4_INVENTORY_QUALITY_GATE.md) |
| v0.5 | Agent Command Contract | AI-to-agent requests can be constrained to an allowlisted schema. | [docs/V0_5_AGENT_COMMAND_CONTRACT.md](docs/V0_5_AGENT_COMMAND_CONTRACT.md) |
| v0.6 | Agent Policy Engine | Default-deny policy can gate validated requests. | [docs/V0_6_AGENT_POLICY_ENGINE.md](docs/V0_6_AGENT_POLICY_ENGINE.md) |
| v0.7 | Agent Audit Log | Policy decisions can produce redacted audit events. | [docs/V0_7_AGENT_AUDIT_LOG.md](docs/V0_7_AGENT_AUDIT_LOG.md) |
| v0.8 | Agent Approval Ledger | Approval outcomes can be recorded without exposing raw request data. | [docs/V0_8_AGENT_APPROVAL_LEDGER.md](docs/V0_8_AGENT_APPROVAL_LEDGER.md) |
| v0.9 | Agent Capability Registry | Generic future agent capabilities can be validated before simulation. | [docs/V0_9_AGENT_CAPABILITY_REGISTRY.md](docs/V0_9_AGENT_CAPABILITY_REGISTRY.md) |
| v1.0 | Read-only Agent Simulator | Contract, policy, approval, and capability checks can be combined without execution. | [docs/V1_0_READ_ONLY_AGENT_SIMULATOR.md](docs/V1_0_READ_ONLY_AGENT_SIMULATOR.md) |
| v1.1 | Agent Dry-Run Plan Renderer | Simulated decisions can become public-safe operator plans. | [docs/V1_1_AGENT_DRY_RUN_PLAN_RENDERER.md](docs/V1_1_AGENT_DRY_RUN_PLAN_RENDERER.md) |
| v1.2 | Agent Runbook Preview | Dry-run plans can become reviewable runbook sections. | [docs/V1_2_AGENT_RUNBOOK_PREVIEW.md](docs/V1_2_AGENT_RUNBOOK_PREVIEW.md) |
| v1.3 | Agent Handoff Packet | Runbook previews can become final handoff packets. | [docs/V1_3_AGENT_HANDOFF_PACKET.md](docs/V1_3_AGENT_HANDOFF_PACKET.md) |
| v1.3.1 | Public README + Release Index Polish | Public presentation can explain the project quickly without new runtime behavior. | [docs/RELEASE_INDEX.md](docs/RELEASE_INDEX.md) |

For a fuller layer-by-layer view, see [docs/RELEASE_INDEX.md](docs/RELEASE_INDEX.md).

## Quick Validation

```bash
bash scripts/doctor.sh
bash scripts/security-scan.sh
```

## Portfolio Value

This repository is useful as a public engineering artifact because it shows:

- local-first architecture;
- security boundaries for public-safe examples;
- policy validation before execution;
- approval workflow modeling;
- redacted audit trail generation;
- dry-run planning from simulated decisions;
- runbook preview rendering;
- handoff packet preparation for future private review or agent layers.

## Local Commands

Initialize ignored local inventory files:

```bash
bash scripts/init-local-inventory.sh
```

Validate local inventory:

```bash
python3 scripts/validate-inventory.py
```

Print a safe inventory summary without writing a report:

```bash
python3 scripts/summarize-inventory.py
```

Validate inventory and write the ignored local report:

```bash
bash scripts/report-inventory.sh
```

Run the safe inventory quality gate without writing a report:

```bash
python3 scripts/check-inventory-quality.py
```

Validate inventory and write the ignored quality report:

```bash
bash scripts/check-inventory-quality.sh
```

Validate the safe agent command examples without writing a report:

```bash
python3 scripts/validate-agent-command.py
```

Validate the safe agent command examples and write the ignored command contract report:

```bash
bash scripts/check-agent-command.sh
```

Evaluate the safe example command against the safe local policy without writing a report:

```bash
python3 scripts/evaluate-agent-policy.py
```

Validate the safe policy flow and write the ignored policy report:

```bash
bash scripts/check-agent-policy.sh
```

Generate a safe redacted agent audit event without writing runtime files:

```bash
python3 scripts/record-agent-audit.py
```

Validate the safe audit flow and write ignored audit runtime files:

```bash
bash scripts/check-agent-audit.sh
```

Generate a safe redacted agent approval event without writing runtime files:

```bash
python3 scripts/record-agent-approval.py
```

Validate the safe approval flow and write ignored approval runtime files:

```bash
bash scripts/check-agent-approval.sh
```

Validate the safe capability registry without writing a report:

```bash
python3 scripts/validate-agent-capability.py
```

Validate the safe capability flow and write the ignored capability summary:

```bash
bash scripts/check-agent-capability.sh
```

Run the end-to-end read-only agent simulator without writing runtime files:

```bash
python3 scripts/simulate-readonly-agent.py
```

Validate the safe simulator flow and write ignored runtime simulation outputs:

```bash
bash scripts/check-readonly-agent-simulator.sh
```

Render a safe dry-run operational plan without writing runtime files:

```bash
python3 scripts/render-dry-run-plan.py
```

Validate the dry-run plan renderer and write ignored runtime dry-run outputs:

```bash
bash scripts/check-dry-run-plan.sh
```

Render a safe public runbook preview without writing runtime files:

```bash
python3 scripts/render-runbook-preview.py
```

Validate the runbook preview renderer and write ignored runtime preview outputs:

```bash
bash scripts/check-runbook-preview.sh
```

Render a safe public handoff packet without writing runtime files:

```bash
python3 scripts/render-handoff-packet.py
```

Validate the handoff packet renderer and write ignored runtime packet outputs:

```bash
bash scripts/check-handoff-packet.sh
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/PUBLIC_SAFETY_BOUNDARY.md](docs/PUBLIC_SAFETY_BOUNDARY.md)
- [docs/SECURITY_BOUNDARIES.md](docs/SECURITY_BOUNDARIES.md)
- [docs/RELEASE_INDEX.md](docs/RELEASE_INDEX.md)

Release screenshots can be kept outside the repository for portfolio posts.

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

## No Secrets Policy

Do not commit secrets or sensitive operational data. Public examples must be fake and sanitized. Treat this repository as shareable by default.

## Future Console Integration

Future versions may expose the sanitized schemas and local data layout to HALO Console as a read-only source of fake inventory, services, and runbook metadata. A private operational deployment would keep any real data outside this public repository.
