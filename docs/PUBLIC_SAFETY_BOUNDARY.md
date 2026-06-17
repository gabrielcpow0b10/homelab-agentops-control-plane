# Public Safety Boundary

This repository is the public sanitized prototype of HomeLab Control Plane. It is suitable for portfolio review because it contains fake examples, schemas, documentation, and local validation tooling only.

It is not the private operational HomeLab repository.

## What Is Included

- Sanitized device and service inventory examples.
- Sanitized runbook reference examples.
- JSON schemas for inventory and agent-related records.
- Local validation, reporting, quality gate, policy, audit, doctor, and security scan scripts.
- Documentation for the Inventory, Safe Summary, Inventory Quality Gate, Agent Command Contract, Agent Policy Engine, and Agent Audit Log architecture.
- Fake example data that is safe to inspect publicly.

## What Is Excluded

- Real inventory.
- Real policies.
- Runtime logs.
- Real device names.
- Real hosts, IP addresses, private paths, URLs, tokens, or secrets.
- Passwords, API keys, SSH keys, private keys, `.env` content, or credentials.
- Screenshots, uploads, private documents, PDFs, or local machine artifacts.
- Network scanning output, agent execution output, or remote automation logs.

## Why This Repo Is Public-Safe

- The examples are fake and generic.
- Runtime output paths are ignored by version control.
- The audit flow records redacted classifications and hashes, not raw operational values.
- The policy engine evaluates default-deny decisions without executing commands or contacting agents.
- The command contract validator blocks arbitrary shell actions and sensitive access patterns.
- The doctor and security scan scripts provide repeatable checks before sharing changes.

## Public Prototype vs. Private Operational Deployment

The public prototype demonstrates the architecture and safety model with sanitized inputs. It shows how a local-first HomeLab control plane can structure inventory records, validate AI-to-agent requests, apply policy gates, and produce redacted audit events.

A private operational deployment would be separate. It could use the same patterns with real local inventory, policies, runtime reports, and audit records, but those artifacts must remain outside this public repository and inside ignored local paths.
