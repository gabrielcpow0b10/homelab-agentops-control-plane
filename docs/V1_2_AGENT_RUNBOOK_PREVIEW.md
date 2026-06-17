# v1.2-local Public Agent Runbook Preview

## Purpose

v1.2-local adds a safe Agent Runbook Preview renderer. It turns the existing dry-run plan into a human-readable operational runbook preview that shows what an operator would review before any future private execution layer exists.

The renderer is local, redacted, and public-safe. It stores only hashes, classifications, counts, section statuses, and safety confirmations.

## Why v1.2 Matters

v1.1 made the simulated agent decision readable as a dry-run plan. v1.2 makes that plan look like an AgentOps review artifact: an operator can see what is ready, what needs approval, what is blocked, and what is never executed.

This moves the public portfolio from validation output toward a control-plane workflow while keeping the repository sanitized.

## Safety Model

The runbook preview preserves the strict public boundary:

- No command execution.
- No shell execution from the Python renderer.
- No subprocess usage in the Python renderer.
- No network contact.
- No agent contact.
- No filesystem mutation unless explicit runtime write flags are used.
- Inputs must resolve inside the repository before they are read.
- Sensitive input patterns block the preview and return a failing exit code.
- Runtime writes are refused for unsafe validation results.
- Runtime writes refuse to overwrite tracked targets.
- Raw command, policy, capability, approval, operator, host, IP, URL, path, token, and secret data is omitted.

## Full Pipeline

The runbook preview builds on the existing dry-run plan renderer:

1. Command Contract Validation.
2. Policy Evaluation.
3. Approval Check.
4. Capability Match.
5. Simulation Decision.
6. Dry-Run Plan.
7. Runbook Preview Rendering.

The preview does not create a new execution path. It imports the dry-run renderer in memory and turns the redacted plan into generic runbook sections.

## What Is Rendered

The JSON preview includes:

- `schemaVersion`.
- `resultType`.
- `previewId`.
- `createdAt`.
- `dryRunPlanFingerprint`.
- `finalSimulationResult`.
- `planStatus`.
- `runbookStatus`.
- `runbookMode`.
- `riskLevel`.
- `approvalRequired`.
- `approvalDecision`.
- `matchedCapabilityCount`.
- `validationErrorCount`.
- `sensitiveInputBlocked`.
- Generic runbook sections.
- Safety confirmations.
- Redaction confirmations.

The default Markdown summary includes result status, runbook status, plan status, final simulation result, approval state, capability count, section count, safety booleans, validation error count, and sensitive input status.

## What Is Never Executed

The runbook preview never executes:

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
python3 scripts/render-runbook-preview.py --write-runtime-preview --write-runtime-summary
```

The runtime files are:

- `runtime/agent-runbook-preview.local.json`.
- `runtime/agent-runbook-preview-summary.local.md`.

These files are ignored by Git and are local-only.

## What Is Never Recorded

The runbook preview never records raw:

- Request IDs.
- Device IDs.
- Service IDs.
- Policy IDs.
- Operator names.
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

## Runbook Status Behavior

`RUNBOOK_PREVIEW_READY` means the dry-run plan is ready, validation was safe, and no approval gap remains.

`RUNBOOK_PREVIEW_REQUIRES_APPROVAL` means the dry-run plan is safe to review but approval is still required. This is a passing preview state because the renderer explains the approval boundary without authorizing execution.

`RUNBOOK_PREVIEW_BLOCKED` means validation failed, policy denied the request, capability matching failed, sensitive input was detected, approval was denied or expired, an unsafe path was rejected, or another safety guard blocked the preview.

## Runtime-Only Local Files

Default mode prints a safe Markdown summary and writes nothing:

```bash
python3 scripts/render-runbook-preview.py
```

Runtime writes require explicit flags:

```bash
python3 scripts/render-runbook-preview.py --write-runtime-preview
python3 scripts/render-runbook-preview.py --write-runtime-summary
```

The renderer creates `runtime/` when needed and refuses to overwrite tracked runtime targets.

## Commands

Run with safe defaults:

```bash
python3 scripts/render-runbook-preview.py
```

Run with explicit safe examples:

```bash
python3 scripts/render-runbook-preview.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.health-check.example.json
```

Run an approval-required preview with an approved decision:

```bash
python3 scripts/render-runbook-preview.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.restart-service.requires-approval.example.json \
  --approval-decision approved
```

Write ignored runtime preview files:

```bash
python3 scripts/render-runbook-preview.py --write-runtime-preview --write-runtime-summary
```

Run the local check script:

```bash
bash scripts/check-runbook-preview.sh
```

Run the full doctor flow:

```bash
bash scripts/doctor.sh
```

## Raspberry Pi 8GB Agent Preparation

The public example capability registry includes a generic Raspberry Pi worker class. v1.2 does not contact that class or any real device. It shows how a future small agent class could be represented in a reviewable runbook preview before any private handoff or execution layer is introduced.

This prepares Raspberry Pi 8GB agents by making the control-plane review step explicit: policy, approval, capability, and dry-run status must be understandable before the agent is allowed to prepare anything.

## Limitations

- The renderer is not an executor.
- The renderer does not prove that a real agent exists.
- The renderer does not inspect real hosts, services, logs, or files.
- The renderer does not validate JSON Schema files directly.
- Fingerprints are short hashes for correlation only, not a cryptographic audit ledger.
- Approval decisions are local preview inputs, not loaded from a real approval system.
- Runtime preview files are local artifacts and must stay ignored.

## v1.3 Next Step

v1.3 idea: Public Agent Handoff Packet.

That milestone could package the runbook preview into a sanitized handoff artifact that a future private agent layer could consume, still without storing raw operational data in the public repository.
