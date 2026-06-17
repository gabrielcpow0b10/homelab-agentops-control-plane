# v0.7-local Agent Audit Log

## Purpose

The Agent Audit Log records a redacted policy evaluation event for future agent workflows. It is an audit-record generation milestone only.

It does not execute commands, contact agents, contact network services, or write real infrastructure details.

## Safety Model

The intended flow is:

1. AI proposes a structured command request.
2. Agent Command Contract validates the request shape and safety.
3. Agent Policy Engine evaluates whether the request is allowed by local policy.
4. Agent Audit Log records a redacted policy evaluation event.
5. A future execution layer may run only after validation, policy, approval, and audit requirements pass.

This milestone implements step 4 only.

## What Gets Recorded

Audit events use schema version `0.7` and event type `agent_policy_evaluation`.

The event stores:

- A generated audit event ID.
- UTC creation time.
- Short SHA-256 based hashes for request, target device, target service, and policy references.
- Short SHA-256 based fingerprints for canonical command and policy JSON.
- Action class, risk level, contract validation result, policy evaluation result, and approval requirement.
- Fixed false values for execution attempted, network contacted, and agent contacted.
- Redaction proof fields showing raw operational data was omitted.

## What Is Never Recorded

Audit events must never store raw request IDs, target device IDs, target service IDs, policy IDs, reasons, parameters, hostnames, IP addresses, URLs, file paths, tokens, secrets, command JSON, or policy JSON.

Normal output is a safe Markdown summary. It reports only status, classifications, counts, and safety flags.

## Hash And Fingerprint Approach

The script hashes raw local identifiers before they enter the audit event. It also hashes canonical command and policy JSON so future local tooling can correlate equivalent inputs without storing the original values.

The hashes are intentionally short. They are useful for local correlation, not for proving identity, preventing all collisions, or protecting weak source values from guessing. The safety boundary still depends on keeping raw local inputs out of the audit record.

## Runtime-Only Local Audit Files

Default mode does not write runtime files.

Optional runtime output is ignored by Git:

- `runtime/agent-audit.local.jsonl`
- `runtime/agent-audit-summary.local.md`

The script creates `runtime/` when optional runtime output is requested. Runtime audit records contain one redacted JSON event per line.

## Commands

Generate a safe redacted audit event without writing runtime files:

```bash
python3 scripts/record-agent-audit.py
```

Generate a safe event from explicit local files:

```bash
python3 scripts/record-agent-audit.py examples/agent-policy.local.example.json examples/agent-command.health-check.example.json
```

Append a runtime JSONL event and write a safe runtime summary:

```bash
python3 scripts/record-agent-audit.py --append-runtime-log --write-runtime-summary examples/agent-policy.local.example.json examples/agent-command.health-check.example.json
```

Run the local audit check:

```bash
bash scripts/check-agent-audit.sh
```

## Raspberry Pi 8GB Agent Preparation

This audit layer gives future Raspberry Pi 8GB agents a local record requirement before execution exists. A future Pi agent can require a command to pass contract validation, policy evaluation, approval checks, and audit generation before any action is eligible to run.

Keeping audit generation separate from execution makes the future agent workflow easier to inspect and safer to extend.

## Limitations

- No command execution exists in this milestone.
- No agent contact exists in this milestone.
- No network service contact exists in this milestone.
- Audit validation uses local standard-library checks.
- Short hashes are correlation aids, not cryptographic proof of uniqueness.
- Redacted audit records are less useful for debugging than raw records by design.

## v0.8 Next Step

The next milestone idea is an Approval Ledger that records local approval decisions separately from command proposal, policy evaluation, audit generation, and future execution.
