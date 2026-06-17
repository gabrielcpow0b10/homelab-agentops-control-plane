# v1.3-local Agent Handoff Packet

## Purpose

v1.3-local adds a safe Agent Handoff Packet renderer. It turns the existing runbook preview into a final public-safe packet for a future private agent layer or human reviewer.

The packet is local, redacted, and public-safe. It stores only hashes, classifications, counts, checklist statuses, and safety confirmations.

## Why v1.3 Matters

v1.2 made the dry-run plan readable as a public-safe runbook preview. v1.3 closes the public AgentOps workflow by packaging that preview into a final handoff artifact:

```text
validate -> simulate -> plan -> preview runbook -> prepare handoff packet
```

This makes the repository look like a complete control-plane workflow without introducing execution, network contact, agent contact, or private operational data.

## Safety Model

The handoff packet keeps the same strict public boundary:

- No command execution.
- No shell execution from the Python renderer.
- No subprocess usage in the Python renderer.
- No network contact.
- No agent contact.
- No filesystem mutation unless explicit runtime write flags are used.
- Inputs must resolve inside the repository before they are read.
- Sensitive input patterns block the packet and return a failing exit code.
- Runtime writes are refused for unsafe validation results.
- Runtime writes refuse to overwrite tracked targets.
- Raw command, policy, capability, approval, reviewer, host, IP, URL, path, token, and secret data is omitted.

## Full Pipeline

The handoff packet builds on the existing runbook preview renderer:

1. Command Contract Validation.
2. Policy Evaluation.
3. Approval Check.
4. Capability Match.
5. Simulation Decision.
6. Dry-Run Plan.
7. Runbook Preview.
8. Handoff Packet Rendering.

The renderer imports the runbook preview renderer in memory. It does not create a new execution path and does not call external services.

## What Is Rendered

The JSON packet includes:

- `schemaVersion`.
- `resultType`.
- `packetId`.
- `createdAt`.
- `runbookPreviewFingerprint`.
- `finalSimulationResult`.
- `planStatus`.
- `runbookStatus`.
- `handoffStatus`.
- `handoffMode`.
- `riskLevel`.
- `approvalRequired`.
- `approvalDecision`.
- `matchedCapabilityCount`.
- `nextActorType`.
- `validationErrorCount`.
- `sensitiveInputBlocked`.
- Generic handoff checklist items.
- Safety confirmations.
- Redaction confirmations.

The default Markdown summary includes result status, handoff status, runbook status, plan status, final simulation result, approval state, capability count, checklist count, next actor type, safety booleans, validation error count, and sensitive input status.

## What Is Never Executed

The handoff packet never executes:

- Agent commands.
- Shell commands.
- Network calls.
- Agent calls.
- Service restarts.
- Backup jobs.
- Package installation.
- Arbitrary command strings.
- Remote automation.

## What Gets Recorded

Runtime JSON and Markdown outputs are written only when explicitly requested:

```bash
python3 scripts/render-handoff-packet.py --write-runtime-packet --write-runtime-summary
```

The runtime files are:

- `runtime/agent-handoff-packet.local.json`.
- `runtime/agent-handoff-packet-summary.local.md`.

These files are ignored by Git and are local-only.

## What Is Never Recorded

The handoff packet never records raw:

- Request IDs.
- Device IDs.
- Service IDs.
- Policy IDs.
- Reviewer identities.
- Email addresses.
- Reason text.
- Command parameters.
- Command JSON.
- Policy JSON.
- Capability JSON.
- Agent identifiers.
- Hostnames.
- IP addresses.
- URLs.
- File paths.
- Tokens.
- Secrets.

## Handoff Status Behavior

`HANDOFF_READY` means the runbook preview is ready, validation was safe, and no approval gap remains.

`HANDOFF_REQUIRES_APPROVAL` means the packet is safe to review but approval is still required. This is a passing packet state because the renderer explains the approval boundary without authorizing execution.

`HANDOFF_BLOCKED` means validation failed, policy denied the request, capability matching failed, sensitive input was detected, approval was denied or expired, an unsafe path was rejected, or another safety guard blocked the packet.

## Runtime-Only Local Files

Default mode prints a safe Markdown summary and writes nothing:

```bash
python3 scripts/render-handoff-packet.py
```

Runtime writes require explicit flags:

```bash
python3 scripts/render-handoff-packet.py --write-runtime-packet
python3 scripts/render-handoff-packet.py --write-runtime-summary
```

The renderer creates `runtime/` when needed and refuses to overwrite tracked runtime targets.

## Commands

Run with safe defaults:

```bash
python3 scripts/render-handoff-packet.py
```

Run with explicit safe examples:

```bash
python3 scripts/render-handoff-packet.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.health-check.example.json
```

Run an approval-required handoff packet with an approved decision:

```bash
python3 scripts/render-handoff-packet.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.restart-service.requires-approval.example.json \
  --approval-decision approved
```

Write ignored runtime packet files:

```bash
python3 scripts/render-handoff-packet.py --write-runtime-packet --write-runtime-summary
```

Run the local check script:

```bash
bash scripts/check-handoff-packet.sh
```

Run the full doctor flow:

```bash
bash scripts/doctor.sh
```

## Raspberry Pi 8GB Agent Preparation

The public example capability registry includes a generic Raspberry Pi worker class. v1.3 does not contact that class or any real device. It shows how a future Raspberry Pi 8GB private agent layer could receive a sanitized handoff signal after policy, approval, capability, simulation, dry-run, and runbook preview checks have already been summarized.

This prepares Raspberry Pi 8GB agents by making the public control-plane boundary explicit: the public repo can prepare a redacted packet, while private execution remains outside the repository.

## Limitations

- The renderer is not an executor.
- The renderer does not prove that a real agent exists.
- The renderer does not inspect real hosts, services, logs, or files.
- The renderer does not validate JSON Schema files directly.
- Fingerprints are short hashes for correlation only, not a cryptographic audit ledger.
- Approval decisions are local renderer inputs, not loaded from a real approval system.
- Runtime handoff files are local artifacts and must stay ignored.

## v1.4 Next Step

v1.4 idea: Public Agent Handoff Receipt.

That milestone could produce a public-safe receipt confirming that a handoff packet was prepared or declined, still without recording raw operational data or contacting a private agent layer.
