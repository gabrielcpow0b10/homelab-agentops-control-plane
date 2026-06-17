# Release Index

This index maps the public-safe milestones in the HomeLab AgentOps Control Plane. It is documentation only and does not add runtime capability.

## Pipeline

```text
AI request
  -> Command Contract
  -> Policy Engine
  -> Approval Ledger
  -> Capability Registry
  -> Read-only Simulator
  -> Dry-Run Plan
  -> Runbook Preview
  -> Handoff Packet
  -> No execution in public repo
```

## Milestones

| Milestone | Layer | What it proves | Safety boundary | Command or doc reference |
| --- | --- | --- | --- | --- |
| v0.2 Local Inventory Runtime | Inventory runtime | Local inventory can be initialized and validated outside tracked public data. | Real inventory belongs in ignored local paths. | [V0_2_LOCAL_INVENTORY_RUNTIME.md](V0_2_LOCAL_INVENTORY_RUNTIME.md), `bash scripts/init-local-inventory.sh`, `python3 scripts/validate-inventory.py` |
| v0.3 Safe Inventory Summary | Inventory reporting | Local inventory can be summarized with redacted counts. | Summary output avoids raw hosts, IPs, URLs, and private paths. | [V0_3_SAFE_INVENTORY_SUMMARY.md](V0_3_SAFE_INVENTORY_SUMMARY.md), `python3 scripts/summarize-inventory.py` |
| v0.4 Inventory Quality Gate | Inventory validation | Inventory hygiene can be checked before downstream use. | Quality output is PASS/WARN/FAIL and public-safe. | [V0_4_INVENTORY_QUALITY_GATE.md](V0_4_INVENTORY_QUALITY_GATE.md), `python3 scripts/check-inventory-quality.py` |
| v0.5 Agent Command Contract | Request contract | AI-to-agent requests can be constrained to an allowlisted JSON contract. | Blocks arbitrary shell and sensitive access patterns. | [V0_5_AGENT_COMMAND_CONTRACT.md](V0_5_AGENT_COMMAND_CONTRACT.md), `python3 scripts/validate-agent-command.py` |
| v0.6 Agent Policy Engine | Policy validation | Validated commands can be evaluated by default-deny policy. | No command execution, network contact, or agent contact. | [V0_6_AGENT_POLICY_ENGINE.md](V0_6_AGENT_POLICY_ENGINE.md), `python3 scripts/evaluate-agent-policy.py` |
| v0.7 Agent Audit Log | Audit trail | Policy decisions can produce redacted audit events. | Audit records use hashes, classifications, and counts only. | [V0_7_AGENT_AUDIT_LOG.md](V0_7_AGENT_AUDIT_LOG.md), `python3 scripts/record-agent-audit.py` |
| v0.8 Agent Approval Ledger | Approval workflow | Human/operator approval outcomes can gate future execution paths. | Denied and expired decisions do not authorize execution. | [V0_8_AGENT_APPROVAL_LEDGER.md](V0_8_AGENT_APPROVAL_LEDGER.md), `python3 scripts/record-agent-approval.py` |
| v0.9 Agent Capability Registry | Capability matching | Generic future agent classes can be matched against safe actions. | Capability examples avoid real deployment details. | [V0_9_AGENT_CAPABILITY_REGISTRY.md](V0_9_AGENT_CAPABILITY_REGISTRY.md), `python3 scripts/validate-agent-capability.py` |
| v1.0 Read-only Agent Simulator | Read-only simulation | Contract, policy, approval, and capability checks can produce a simulated decision. | Simulation does not execute commands or write by default. | [V1_0_READ_ONLY_AGENT_SIMULATOR.md](V1_0_READ_ONLY_AGENT_SIMULATOR.md), `python3 scripts/simulate-readonly-agent.py` |
| v1.1 Agent Dry-Run Plan Renderer | Dry-run planning | A simulated decision can become a human-readable plan. | Plan output is redacted and no-write by default. | [V1_1_AGENT_DRY_RUN_PLAN_RENDERER.md](V1_1_AGENT_DRY_RUN_PLAN_RENDERER.md), `python3 scripts/render-dry-run-plan.py` |
| v1.2 Agent Runbook Preview | Runbook preview | A dry-run plan can become operator review sections. | Preview output omits raw operational values. | [V1_2_AGENT_RUNBOOK_PREVIEW.md](V1_2_AGENT_RUNBOOK_PREVIEW.md), `python3 scripts/render-runbook-preview.py` |
| v1.3 Agent Handoff Packet | Handoff packet | A runbook preview can become a final handoff packet. | Packet output remains public-safe and does not authorize real execution. | [V1_3_AGENT_HANDOFF_PACKET.md](V1_3_AGENT_HANDOFF_PACKET.md), `python3 scripts/render-handoff-packet.py` |
| v1.3.1 Public README + Release Index Polish | Public documentation | A visitor can understand the project, pipeline, safety boundary, and release map quickly. | Documentation polish only; no new runtime capability. | [README.md](../README.md), [CHANGELOG.md](../CHANGELOG.md) |

Release screenshots can be kept outside the repository for portfolio posts.
