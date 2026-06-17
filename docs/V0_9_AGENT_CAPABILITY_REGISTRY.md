# v0.9-local Agent Capability Registry

## Purpose

v0.9-local adds a safe local Agent Capability Registry. The registry documents generic future agent classes and the safe action categories they may support without identifying real devices, hosts, addresses, service names, deployment locations, or operators.

This milestone does not execute commands, contact agents, or contact network services.

## Safety Model

The intended flow is:

1. AI proposes a structured Agent Command Contract request.
2. The Agent Command Contract validates request shape and safety.
3. The Agent Policy Engine evaluates default-deny policy rules.
4. The Agent Audit Log records a redacted policy evaluation event.
5. The Agent Approval Ledger records a redacted approval decision when required.
6. The Agent Capability Registry validates whether at least one enabled generic agent class claims the capability needed for the requested action.
7. Future execution layers remain out of scope for this milestone.

v0.9-local implements only local capability registry validation.

## What Gets Recorded

The public-safe registry stores:

- `schemaVersion`, `registryType`, and `generatedFor`.
- Generic `agentClassId` and `displayName` values.
- Whether an agent class is enabled.
- Generic runtime class: `raspberry_pi`, `mac_mini`, `linux_server`, `container`, or `other`.
- Supported action categories.
- Supported modes.
- Maximum risk level.
- Actions requiring approval by capability.
- Denied actions.
- Safety flags that must all be `true`.
- A notes classification such as `public_example` or `planned`.

The validator prints a safe Markdown summary with counts and PASS, WARN, or FAIL status.

## What Is Never Recorded

The registry and reports must never store:

- Real agent IDs.
- Real device IDs.
- Real service IDs.
- Real hostnames.
- Real network addresses.
- Real service URLs.
- Real file paths.
- Real usernames or emails.
- Tokens or secrets.
- Raw operational notes.
- Private inventory, private policy, audit, or approval data.
- Raw command request IDs, target IDs, reason text, or parameters.

## Relationship To Earlier Milestones

- The Agent Command Contract validates the command JSON before capability matching.
- The Agent Policy Engine evaluates default-deny policy rules before any future execution layer.
- The Agent Audit Log records redacted policy evaluation events.
- The Agent Approval Ledger records redacted approval decisions when required.
- The Agent Capability Registry adds one more local gate: an enabled generic class must support the requested action, mode, and risk level.

The registry does not override policy, approval, or command validation. It only says whether a future class claims a safe capability category.

## PASS, WARN, And FAIL

- `PASS`: the registry is valid, and an optional command has at least one enabled matching capability with no blocking errors.
- `WARN`: the registry is valid, but a matching capability requires approval or is marked as planned or limited.
- `FAIL`: the registry is invalid, sensitive input is detected, a path is outside the repository, command validation fails, no enabled capability matches, the risk level is too high, the mode is unsupported, or the action is denied.

`PASS` and `WARN` exit with status code `0`. `FAIL` exits with status code `1`.

## Runtime-Only Local Summary

Default validation does not write runtime files.

Optional runtime output is:

- `runtime/agent-capability-summary.local.md`

This file is ignored by Git and contains only safe summary counts and flags. The script refuses to overwrite tracked files and writes the summary only after validation passes or warns.

## Commands

Validate the safe example registry:

```bash
python3 scripts/validate-agent-capability.py
```

Validate the safe example registry with a safe command:

```bash
python3 scripts/validate-agent-capability.py examples/agent-capability.local.example.json examples/agent-command.health-check.example.json
```

Validate and write the ignored runtime summary:

```bash
python3 scripts/validate-agent-capability.py --write-runtime-summary examples/agent-capability.local.example.json examples/agent-command.health-check.example.json
```

Run the local capability check:

```bash
bash scripts/check-agent-capability.sh
```

Run the full local doctor:

```bash
bash scripts/doctor.sh
```

## Raspberry Pi 8GB Agent Preparation

The registry prepares for future Raspberry Pi 8GB agents by defining generic class capabilities before any real agent identity or connection details exist. A private deployment can later map real agents to private class records outside this public repository, while this repository keeps only fake public examples and local validation behavior.

## Limitations

- No real agent discovery is implemented.
- No command execution is implemented.
- No network or agent contact is implemented.
- JSON Schema is included for documentation, but validation is implemented with Python standard-library code.
- Capability matching is class-based, not instance-based.
- The current command contract uses `restart_allowed_service`; this registry maps that command action to the public capability name `restart_service`.

## v1.0 Next Step

v1.0-local can add a Read-only Agent Simulator that consumes validated commands, policy decisions, approvals, and capability matches, then produces fake redacted simulator output without contacting real agents.
