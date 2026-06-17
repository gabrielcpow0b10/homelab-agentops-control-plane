# v0.8-local Agent Approval Ledger

## Purpose

v0.8-local adds a safe local Agent Approval Ledger for future agent workflows. It records whether a human/operator approval decision was granted, denied, or expired after command validation, policy evaluation, and audit logging.

This milestone does not execute commands, contact agents, or contact network services.

## Safety Model

The intended flow is:

1. AI proposes a structured Agent Command Contract request.
2. The Agent Command Contract validates request shape and safety.
3. The Agent Policy Engine evaluates default-deny policy rules.
4. The Agent Audit Log records a redacted policy evaluation event.
5. The Agent Approval Ledger records a redacted approval decision.
6. Future execution layers may proceed only when validation, policy, audit, and approval requirements all pass.

v0.8-local implements only the approval-record generation and validation layer.

## What Gets Recorded

Approval events store:

- `schemaVersion` and `eventType`.
- A SHA-256 based approval event fingerprint.
- UTC creation time.
- Short SHA-256 reference hashes for request, target device, target service, and policy.
- Short SHA-256 fingerprints for canonical command and policy JSON.
- Action class and risk level.
- Policy evaluation result.
- Whether approval was required.
- Approval decision: `approved`, `denied`, or `expired`.
- Approval scope: `single_request`.
- A short SHA-256 hash of a safe operator reference.
- A reason classification, not reason text.
- Expiry timestamp or `none`.
- Whether execution would be authorized by this decision.
- Proof flags that raw sensitive fields were omitted.

## What Is Never Recorded

Approval events must never store:

- Raw request IDs.
- Raw target device IDs.
- Raw target service IDs.
- Raw policy IDs.
- Raw operator names.
- Raw emails.
- Raw reason text.
- Raw parameters.
- Raw hostnames.
- Raw IP addresses.
- Raw URLs.
- Raw file paths.
- Raw tokens or secrets.
- Raw command JSON.
- Raw policy JSON.

## Approval Decisions

- `approved`: records that the approval gate was granted.
- `denied`: records that the approval gate was rejected.
- `expired`: records that the approval window is no longer valid.

Denied and expired decisions always produce `executionAuthorized: false`.

## executionAuthorized Rules

- `DENY` policy results always produce `executionAuthorized: false`, even with an approved decision.
- `ALLOW_WITH_APPROVAL` produces `executionAuthorized: true` only when approval is required and the decision is `approved`.
- `ALLOW` with no approval requirement may produce `executionAuthorized: true` when the recorded decision is `approved`.
- Any `denied` or `expired` decision produces `executionAuthorized: false`.
- `executionAttempted`, `networkContacted`, and `agentContacted` are always `false` in this milestone.

## Hash Approach and Limitations

The ledger uses short SHA-256 hashes and canonical JSON fingerprints to avoid storing raw identifiers or raw command/policy documents. Hashes are useful for local correlation, but they are not encryption. Low-entropy identifiers could be guessed by an operator who already knows the candidate values.

For a private deployment, keep raw operational data in ignored local files and treat public examples as sanitized test data only.

## Runtime-Only Local Files

Default mode does not write runtime files.

Optional runtime files are:

- `runtime/agent-approval-ledger.local.jsonl`
- `runtime/agent-approval-summary.local.md`

These files are ignored by Git and are intended for local-only review.

## Commands

Generate a safe approval event without writing runtime files:

```bash
python3 scripts/record-agent-approval.py
```

Generate a safe approval event for explicit inputs:

```bash
python3 scripts/record-agent-approval.py examples/agent-policy.local.example.json examples/agent-command.restart-service.requires-approval.example.json approved
```

Validate the approval flow and write ignored runtime files:

```bash
bash scripts/check-agent-approval.sh
```

Run the full local doctor:

```bash
bash scripts/doctor.sh
```

## Raspberry Pi 8GB Agent Preparation

This milestone prepares Raspberry Pi 8GB agents by defining a local approval record that can be checked before any future execution layer runs. A future agent can require a validated command, a policy result, a redacted audit event, and an approval event before touching any device or service.

The public repository still contains only fake examples and local validation tooling.

## Limitations

- No real command execution is implemented.
- No agent contact is implemented.
- No network service contact is implemented.
- No cryptographic signing is implemented.
- Short hashes support correlation, not secrecy against exhaustive guessing.
- Approval records are local artifacts and are not a distributed ledger.

## v0.9 Next Step

v0.9-local can add an Agent Capability Registry that lists which future agents may support which safe action classes and policy capabilities without storing real hosts, addresses, or private deployment details.
