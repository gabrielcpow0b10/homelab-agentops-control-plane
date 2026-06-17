# v0.6-local Agent Policy Engine

## Purpose

The Agent Policy Engine evaluates validated Agent Command Contract requests against local policy rules. It is a policy-only milestone. It does not execute commands, contact agents, or call network services.

## Safety Model

The intended flow is:

1. AI proposes a structured command request.
2. Agent Command Contract validates the request shape and safety.
3. Agent Policy Engine evaluates whether the request is allowed by local policy.
4. A future execution layer may run only after both validation and policy evaluation allow it.

This milestone implements step 3 only.

## Contract Validation And Policy Evaluation

Contract validation checks whether the command request is structurally safe. Policy evaluation checks whether a locally defined policy allows that validated command for the target device, service, risk level, and approval state.

If contract validation fails, the policy decision is always `DENY`.

## Decisions

`ALLOW` means the command matches a known enabled device policy, the action is allowed, service restrictions pass, and risk is within the configured maximum.

`ALLOW_WITH_APPROVAL` means the command otherwise passes policy evaluation but either the command requests approval or the action is listed in `approvalRequiredActions`.

`DENY` means the command fails contract validation, fails policy validation, targets no matching enabled device policy, uses a denied or unlisted action, fails service restrictions, exceeds max risk, or otherwise does not satisfy policy.

## Default Deny

Policies must set `defaultDecision` to `deny`. Unknown devices, disabled devices, unknown actions, and invalid inputs deny by default.

## Approval Required

Approval is required when:

- The action is listed in the matching device policy `approvalRequiredActions`.
- The command request sets `requiresApproval` to true.

Approval does not execute anything in v0.6-local. It only changes the decision classification to `ALLOW_WITH_APPROVAL`.

## Never Exposed

Normal reports never print raw device IDs, service IDs, reasons, parameters, policy device IDs, allowed service IDs, real hosts, IP addresses, URLs, tokens, secrets, private paths, notes, screenshots, PDFs, uploads, or logs.

Reports are count-based and classification-based.

## Commands

Evaluate the safe example policy and command:

```bash
python3 scripts/evaluate-agent-policy.py
```

Evaluate explicit local files:

```bash
python3 scripts/evaluate-agent-policy.py examples/agent-policy.local.example.json examples/agent-command.health-check.example.json
```

Write the redacted runtime report:

```bash
python3 scripts/evaluate-agent-policy.py --write-runtime-report examples/agent-policy.local.example.json examples/agent-command.health-check.example.json
```

Run the local check:

```bash
bash scripts/check-agent-policy.sh
```

## Raspberry Pi 8GB Agent Preparation

The policy engine defines the decision gate future Raspberry Pi 8GB agents will need before execution exists. A Pi agent can later receive only requests that already passed contract validation and local policy evaluation.

This keeps command proposal, validation, policy, approval, and execution as separate layers.

## Limitations

- No command execution exists in this milestone.
- No agent contact exists in this milestone.
- No network service contact exists in this milestone.
- Policy validation uses local standard-library checks.
- Reports are intentionally redacted and do not provide raw identifiers for debugging.

## v0.7 Next Step

The next milestone idea is an Agent Audit Log that records redacted policy decisions and future execution lifecycle events without exposing private infrastructure details.
