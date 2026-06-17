# v1.1-local Agent Dry-Run Plan Renderer

## Purpose

v1.1-local adds a safe Agent Dry-Run Plan Renderer. It takes the existing read-only simulation result and renders a human-readable operational plan that explains what would happen, without executing anything.

The renderer is intentionally local, redacted, and portfolio-safe. It uses fake public examples and stores only hashes, classifications, counts, step statuses, and safety confirmations.

## Why v1.1 Matters

v1.0 proved that the control plane can make an end-to-end simulated decision across command validation, policy, approval, and capability checks. v1.1 makes that decision reviewable by turning it into a dry-run plan.

That is the step from a validator to an AgentOps control plane: humans can see a safe operational sequence before any future execution layer exists.

## Safety Model

The renderer preserves the same safety boundary as the simulator:

- No command execution.
- No shell execution.
- No subprocess usage in the Python renderer.
- No network contact.
- No agent contact.
- No filesystem mutation unless explicit runtime write flags are used.
- No raw command, policy, capability, approval, operator, host, IP, URL, path, token, or secret data is stored.
- Inputs must resolve inside the repository before they are read.
- Sensitive input patterns block the plan and return a failing exit code.

## Full Pipeline

The dry-run plan renderer uses the v1.0 simulator decision pipeline in memory:

1. Command Contract Validation.
2. Policy Evaluation.
3. Approval Check.
4. Capability Match.
5. Simulation Decision.
6. Dry-Run Result.

The renderer does not create a new execution path. It renders a safe plan from the read-only simulator output.

## What Is Rendered

The JSON plan includes:

- `schemaVersion`.
- `resultType`.
- `planId`.
- `createdAt`.
- `simulationFingerprint`.
- `finalSimulationResult`.
- `planStatus`.
- `planMode`.
- `riskLevel`.
- `approvalRequired`.
- `approvalDecision`.
- `matchedCapabilityCount`.
- `validationErrorCount`.
- `sensitiveInputBlocked`.
- Generic plan steps.
- Safety confirmations.
- Redaction confirmations.

The Markdown summary includes the dry-run result, plan status, final simulation result, approval state, capability count, step count, safety booleans, validation error count, and sensitive input status.

## What Is Never Executed

The renderer never executes:

- Agent commands.
- Shell commands.
- Network calls.
- Agent calls.
- Service restarts.
- Backup runs.
- Package installation.
- Arbitrary command strings.
- Remote automation.

## What Gets Recorded

Runtime JSON and Markdown outputs are written only when explicitly requested:

```bash
python3 scripts/render-dry-run-plan.py --write-runtime-plan --write-runtime-summary
```

The runtime files are:

- `runtime/agent-dry-run-plan.local.json`.
- `runtime/agent-dry-run-plan-summary.local.md`.

These files are ignored by Git and are local-only.

## What Is Never Recorded

The dry-run plan never records raw:

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

## Plan Status Behavior

`PLAN_READY` means the read-only simulator returned `SIMULATED_READY`, validation was safe, and no approval gap remains in the plan.

`PLAN_REQUIRES_APPROVAL` means the simulator returned `SIMULATED_REQUIRES_APPROVAL`. This is a passing dry-run state because the renderer safely explains that human approval is still required.

`PLAN_BLOCKED` means validation failed, policy denied the request, capability matching failed, sensitive input was detected, approval was denied or expired, or another safe internal validation guard blocked the plan.

## Runtime-Only Local Files

Default mode prints a safe Markdown summary and writes nothing:

```bash
python3 scripts/render-dry-run-plan.py
```

Runtime writes require explicit flags:

```bash
python3 scripts/render-dry-run-plan.py --write-runtime-plan
python3 scripts/render-dry-run-plan.py --write-runtime-summary
```

The renderer creates `runtime/` when needed and refuses to overwrite tracked runtime targets.

## Commands

Run with safe defaults:

```bash
python3 scripts/render-dry-run-plan.py
```

Run with explicit safe examples:

```bash
python3 scripts/render-dry-run-plan.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.health-check.example.json
```

Run an approval-required plan with an approved decision:

```bash
python3 scripts/render-dry-run-plan.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.restart-service.requires-approval.example.json \
  --approval-decision approved
```

Run the local check script:

```bash
bash scripts/check-dry-run-plan.sh
```

Run the full doctor flow:

```bash
bash scripts/doctor.sh
```

## Raspberry Pi 8GB Agent Preparation

The public example capability registry includes a generic Raspberry Pi worker class. v1.1 does not contact that class or any real device. Instead, it proves the control plane can explain whether a future small agent class is compatible with a requested action, mode, and risk level.

That prepares the future Raspberry Pi 8GB agent path by keeping the orchestration layer reviewable before execution is introduced.

## Limitations

- The renderer is not an executor.
- The renderer does not prove that a real agent exists.
- The renderer does not inspect real hosts, services, logs, or files.
- The renderer does not validate JSON Schema files directly.
- Fingerprints are short hashes for correlation only, not a cryptographic audit ledger.
- Approval decisions are provided as local dry-run inputs, not loaded from a real approval system.

## v1.2 Next Step

v1.2 idea: Public Agent Runbook Preview.

That milestone would render a safe public runbook preview for a planned agent action, still without execution, network contact, agent contact, or raw operational data.
