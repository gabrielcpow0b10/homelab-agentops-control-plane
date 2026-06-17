# v1.0-local Read-only Agent Simulator

v1.0-local adds a safe read-only simulator for the future agent execution pipeline. It runs local validation and decision logic only. It does not execute commands, contact agents, or contact network services.

## Purpose

The simulator demonstrates the full control-plane flow before any execution layer exists:

1. Validate the Agent Command Contract.
2. Evaluate the default-deny Agent Policy Engine.
3. Check whether approval is required.
4. Check the Agent Capability Registry.
5. Generate a redacted audit-style simulation summary.
6. Produce a final simulated decision.
7. Stop without executing anything.

## Why v1.0 Matters

Earlier milestones validate individual pieces of the control plane. v1.0-local is the first end-to-end read-only milestone. It shows how command, policy, approval, capability, audit-style summary, and final decision behavior fit together while staying safe for a public repository.

## Safety Model

The simulator is local-only and standard-library-only. It enforces repo-local input paths, rejects sensitive input patterns, imports existing local validators, and stores only hashes, counts, classifications, booleans, and timestamps.

It always records:

- `executionAttempted: false`
- `networkContacted: false`
- `agentContacted: false`
- `filesystemMutationAttempted: false`
- `commandExecuted: false`

## Full Pipeline

The default command uses the safe example capability registry, policy, and health-check command:

```bash
python3 scripts/simulate-readonly-agent.py
```

Explicit inputs use:

```bash
python3 scripts/simulate-readonly-agent.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.health-check.example.json
```

Approval-required simulation can pass a safe approval decision:

```bash
python3 scripts/simulate-readonly-agent.py \
  examples/agent-capability.local.example.json \
  examples/agent-policy.local.example.json \
  examples/agent-command.restart-service.requires-approval.example.json \
  --approval-decision approved
```

## What Is Simulated

- Command contract validation.
- Policy decision classification.
- Approval-required logic.
- Approval decision handling for `approved`, `denied`, and `expired`.
- Capability registry matching.
- Redacted simulation result generation.
- Final readiness, blocked, or approval-required decision.

## What Is Never Executed

- Agent commands.
- Shell commands from Python.
- Network calls.
- Agent calls.
- Service restarts.
- Package installs.
- File reads outside repo-local validated input files.
- Any operational HomeLab action.

## What Gets Recorded

The JSON result records only public-safe fields:

- Schema and result type.
- Short SHA-256 based simulation ID.
- UTC creation timestamp.
- Short fingerprints for command, policy, and capability input JSON.
- Pass/fail and classification results.
- Approval required and approval decision classification.
- Matched capability count.
- Validation error count.
- Sensitive-input blocked boolean.
- Redaction proof booleans.

## What Is Never Recorded

The result never stores raw request IDs, device IDs, service IDs, policy IDs, operator names, emails, reason text, parameters, policy content, capability content, hostnames, IP addresses, URLs, file paths, tokens, secrets, raw command JSON, or raw agent identifiers.

## Final Decisions

`SIMULATED_READY` means all validation passed and either no approval was required or the required approval decision was `approved`.

`SIMULATED_BLOCKED` means command validation failed, policy denied the request, capability matching failed, sensitive input was blocked, or a required approval was `denied` or `expired`.

`SIMULATED_REQUIRES_APPROVAL` means command, policy, and capability checks passed, but an approval is required and no approval decision was supplied.

## Runtime-only Local Files

Default mode writes no runtime files.

Optional local runtime output writes ignored files:

```bash
python3 scripts/simulate-readonly-agent.py --write-runtime-result --write-runtime-summary
```

Runtime outputs:

- `runtime/agent-simulation-result.local.json`
- `runtime/agent-simulation-summary.local.md`

The simulator creates `runtime/` when needed, refuses to overwrite tracked runtime outputs, and writes only redacted simulation data.

## Check Command

```bash
bash scripts/check-readonly-agent-simulator.sh
```

The check script runs default, explicit, approval-approved, and runtime-write simulations. It also confirms the runtime outputs are ignored by Git and that no staged changes exist.

## Raspberry Pi 8GB Agent Preparation

This milestone prepares for Raspberry Pi 8GB agents by proving the control-plane decision pipeline before any device runner exists. A future agent can consume the same command, policy, approval, and capability decisions while this public repository continues to show only sanitized examples and no operational details.

## Limitations

- The simulator does not render an execution plan.
- Capability matching uses generic future agent classes only.
- Approval decisions are supplied as local classifications, not read from a real approval system.
- Fingerprints are short hashes for correlation, not a privacy boundary for real operational data.
- This milestone intentionally has no network, agent, or execution layer.

## v1.1 Next Step

v1.1 can add an Agent Dry-Run Plan Renderer. That would produce a redacted step plan for approved or approval-ready requests while continuing to avoid execution and network contact.
