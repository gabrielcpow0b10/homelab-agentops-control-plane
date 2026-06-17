# Changelog

## 1.1.0-local - Agent Dry-Run Plan Renderer

- Added a safe Agent Dry-Run Plan Renderer that turns the v1.0 read-only simulation decision into a human-readable operational plan.
- Added redacted dry-run plan schema and sanitized example plan with generic step objects, classifications, counts, and safety booleans only.
- Added `scripts/render-dry-run-plan.py` with safe defaults, optional approval decisions, optional ignored runtime JSON and Markdown outputs, and no subprocess usage.
- Added `scripts/check-dry-run-plan.sh` and integrated no-write dry-run rendering into doctor.
- Added v1.1-local documentation for safety model, rendered fields, omitted fields, runtime outputs, commands, limitations, and the v1.2 Public Agent Runbook Preview idea.

## 1.0.0-local - Read-only Agent Simulator

- Added a safe read-only Agent Simulator that runs command contract, policy, approval, and capability checks without execution.
- Added redacted simulation result schema and sanitized example result.
- Added `scripts/simulate-readonly-agent.py` with safe defaults, optional approval decisions, optional ignored runtime JSON and Markdown outputs, and pure Python tracked-file guards.
- Added `scripts/check-readonly-agent-simulator.sh` and integrated no-write simulator validation into doctor.
- Added v1.0-local documentation for safety model, full pipeline behavior, recorded fields, omitted fields, runtime outputs, limitations, and the v1.1 Agent Dry-Run Plan Renderer idea.

## 0.9.0-local - Agent Capability Registry

- Added a public-safe Agent Capability Registry schema and sanitized example registry.
- Added `scripts/validate-agent-capability.py` for local capability validation against optional command requests.
- Added optional ignored runtime output for safe capability summaries.
- Added `scripts/check-agent-capability.sh` and integrated no-write capability validation into doctor.
- Added v0.9-local documentation for safety model, recorded fields, omitted fields, PASS/WARN/FAIL behavior, commands, limitations, and the v1.0 Read-only Agent Simulator idea.

## 0.8.0-local - Agent Approval Ledger

- Added a safe redacted Agent Approval Ledger event schema and sanitized example event.
- Added `scripts/record-agent-approval.py` to generate approval decision events from local policy evaluation without executing commands.
- Added optional ignored runtime output for JSONL approval events and safe Markdown summaries.
- Added `scripts/check-agent-approval.sh` and integrated no-write approval generation into doctor.
- Added v0.8-local documentation for recorded fields, omitted fields, authorization rules, hash limitations, commands, and the v0.9 Agent Capability Registry idea.

## 0.7.0-local - Agent Audit Log

- Added a safe redacted Agent Audit Log event schema and sanitized example event.
- Added `scripts/record-agent-audit.py` to generate audit events from local policy evaluation without executing commands.
- Added optional ignored runtime output for JSONL audit events and safe Markdown summaries.
- Added `scripts/check-agent-audit.sh` and integrated no-write audit generation into doctor.
- Added v0.7-local documentation for recorded fields, omitted fields, hash limitations, commands, and the v0.8 Approval Ledger idea.

## 0.6.0-local - Agent Policy Engine

- Added a local Agent Policy Engine for default-deny policy evaluation of validated Agent Command Contract requests.
- Added the agent policy schema, safe local example policy, redacted evaluator, local check script, and v0.6 documentation.
- Integrated policy evaluation into the local doctor flow.
- Kept the milestone policy-only: no command execution, agent contact, network contact, release, push, or dependency changes.

## 0.5.0-local - Agent Command Contract

- Added a safe JSON Agent Command Contract schema for future HomeLab agent requests.
- Added sanitized example command requests for read-only, dry-run, and approval-required flows.
- Added a standard-library validator that rejects blocked actions, unknown actions, unsafe parameters, and sensitive patterns.
- Added an ignored runtime report helper for redacted command contract validation.
- Added doctor checks for command contract shell syntax, Python compilation, and no-write validation.
- Added v0.5-local documentation for the safety model, approval rules, commands, limitations, and the v0.6 Agent Policy Engine idea.

## 0.4.0-local - Inventory Quality Gate

- Added a redacted local inventory quality gate with PASS, WARN, and FAIL results.
- Added duplicate ID, missing owner reference, unknown status, and missing device runbook checks.
- Added an ignored runtime quality report helper.
- Added doctor checks for quality gate shell syntax, Python compilation, and no-write quality execution.
- Added v0.4-local documentation for safety boundaries, commands, limitations, and the v0.5 Agent Command Contract idea.

## 0.3.0-local - Safe Inventory Summary Report

- Added a redacted local inventory summary script.
- Added an ignored runtime report helper for safe local review.
- Added doctor checks for summary script syntax and no-write summary execution.
- Added v0.3-local documentation for safe report contents, exclusions, limitations, and future console integration.

## 0.2.0-local - Local Inventory Runtime

- Added ignored local inventory runtime guidance.
- Added sanitized local device and service inventory templates.
- Added standard-library local inventory validation.
- Added local inventory initialization without overwriting existing files.
- Updated doctor checks to include local inventory validation.
- Added v0.2-local documentation for storage rules, validation, limitations, and next steps.

## 0.1.0 - Initial Bootstrap

- Added public-safe control-plane documentation foundation.
- Added sanitized device, service, and runbook examples.
- Added device and service JSON schemas.
- Added conservative local validation scripts.
- Added security boundaries and repository ignore rules.
