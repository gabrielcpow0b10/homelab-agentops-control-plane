#!/usr/bin/env python3
"""Render a redacted dry-run operational plan from the read-only simulator."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT DRY-RUN PLAN ONLY - NO EXECUTION, NO NETWORK, NO AGENT CONTACT, NO RAW SECRETS"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPABILITY = "examples/agent-capability.local.example.json"
DEFAULT_POLICY = "examples/agent-policy.local.example.json"
DEFAULT_COMMAND = "examples/agent-command.health-check.example.json"
RUNTIME_PLAN = Path("runtime/agent-dry-run-plan.local.json")
RUNTIME_SUMMARY = Path("runtime/agent-dry-run-plan-summary.local.md")
APPROVAL_DECISIONS = {"approved", "denied", "expired"}
PLAN_STATUSES = {"PLAN_READY", "PLAN_BLOCKED", "PLAN_REQUIRES_APPROVAL"}


class SimulatorLoadError(RuntimeError):
    """Raised when the local read-only simulator cannot be imported."""


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    simulator = load_simulator()
    plan = render_plan(args, simulator)
    summary = render_summary(plan)
    print(summary)

    if args.write_runtime_plan or args.write_runtime_summary:
        if not can_write_runtime(plan):
            print("Runtime output blocked because input validation was not safe.")
            return 1
        try:
            if args.write_runtime_plan:
                write_runtime_json(plan, simulator)
                print("Safe runtime dry-run plan written.")
            if args.write_runtime_summary:
                write_runtime_summary(summary, simulator)
                print("Safe runtime dry-run summary written.")
        except RuntimeError:
            print("Runtime output blocked by safety guard.")
            return 1

    return exit_code(plan)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a safe redacted agent dry-run plan.")
    parser.add_argument("paths", nargs="*", help="Optional capability registry, policy, and command JSON files.")
    parser.add_argument("--approval-decision", choices=sorted(APPROVAL_DECISIONS))
    parser.add_argument("--write-runtime-plan", action="store_true")
    parser.add_argument("--write-runtime-summary", action="store_true")
    args = parser.parse_args(argv)
    if len(args.paths) not in {0, 3}:
        parser.error("provide either no paths or exactly capability registry, policy, and command paths")
    return args


def load_simulator() -> Any:
    module_path = REPO_ROOT / "scripts" / "simulate-readonly-agent.py"
    spec = importlib.util.spec_from_file_location("halo_readonly_agent_simulator", module_path)
    if spec is None or spec.loader is None:
        raise SimulatorLoadError("read-only simulator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise SimulatorLoadError("read-only simulator import failed") from exc
    return module


def render_plan(args: argparse.Namespace, simulator: Any) -> dict[str, Any]:
    paths = args.paths if args.paths else [DEFAULT_CAPABILITY, DEFAULT_POLICY, DEFAULT_COMMAND]
    sim_args = argparse.Namespace(
        paths=paths,
        approval_decision=args.approval_decision,
        write_runtime_result=False,
        write_runtime_summary=False,
    )
    simulation = simulator.run_simulation(sim_args)
    simulation_result = simulator.build_result(simulation)
    plan_status = plan_status_for(simulation_result["finalSimulationResult"])
    created_at = simulator.utc_now()
    simulation_fingerprint = simulator.short_hash(
        {
            "commandFingerprint": simulation_result["commandFingerprint"],
            "policyFingerprint": simulation_result["policyFingerprint"],
            "capabilityFingerprint": simulation_result["capabilityFingerprint"],
            "finalSimulationResult": simulation_result["finalSimulationResult"],
            "approvalRequired": simulation_result["approvalRequired"],
            "approvalDecision": simulation_result["approvalDecision"],
            "matchedCapabilityCount": simulation_result["matchedCapabilityCount"],
            "validationErrorCount": simulation_result["validationErrorCount"],
            "sensitiveInputBlocked": simulation_result["sensitiveInputBlocked"],
        }
    )
    plan_id = "plan_" + short_hash(
        {
            "createdAt": created_at,
            "simulationFingerprint": simulation_fingerprint,
            "planStatus": plan_status,
        }
    )
    return {
        "schemaVersion": "1.1",
        "resultType": "agent_dry_run_plan",
        "planId": plan_id,
        "createdAt": created_at,
        "simulationFingerprint": simulation_fingerprint,
        "finalSimulationResult": simulation_result["finalSimulationResult"],
        "planStatus": plan_status,
        "planMode": simulation_result["simulatedActionClass"],
        "riskLevel": simulation_result["simulatedRiskLevel"],
        "approvalRequired": simulation_result["approvalRequired"],
        "approvalDecision": simulation_result["approvalDecision"],
        "matchedCapabilityCount": simulation_result["matchedCapabilityCount"],
        "validationErrorCount": simulation_result["validationErrorCount"],
        "sensitiveInputBlocked": simulation_result["sensitiveInputBlocked"],
        "steps": build_steps(simulation_result, plan_status),
        "safety": safety_proof(),
        "redaction": redaction_proof(),
    }


def plan_status_for(final_result: str) -> str:
    if final_result == "SIMULATED_READY":
        return "PLAN_READY"
    if final_result == "SIMULATED_REQUIRES_APPROVAL":
        return "PLAN_REQUIRES_APPROVAL"
    return "PLAN_BLOCKED"


def build_steps(result: dict[str, Any], plan_status: str) -> list[dict[str, Any]]:
    return [
        step(
            1,
            "Command Contract Validation",
            "READY" if result["commandContractResult"] == "pass" else "BLOCKED",
            "The request shape was checked against the safe command contract.",
            "The raw command request was not stored in the plan.",
        ),
        step(
            2,
            "Policy Evaluation",
            policy_step_status(result["policyEvaluationResult"]),
            "Default-deny policy evaluation produced a redacted decision classification.",
            "Policy content and policy identifiers were omitted.",
        ),
        step(
            3,
            "Approval Check",
            approval_step_status(result),
            approval_summary(result),
            "Operator identity, reason text, and approval ledger details were omitted.",
        ),
        step(
            4,
            "Capability Match",
            capability_step_status(result["capabilityRegistryResult"]),
            "The capability registry was checked for a compatible generic agent class.",
            "Capability content and agent identifiers were omitted.",
        ),
        step(
            5,
            "Simulation Decision",
            simulation_step_status(result["finalSimulationResult"]),
            "The read-only simulator produced a final decision without contacting agents.",
            "No command execution, network access, or agent contact was attempted.",
        ),
        step(
            6,
            "Dry-Run Result",
            dry_run_step_status(plan_status),
            "The final dry-run plan status was rendered for human review.",
            "The plan contains only hashes, classifications, counts, and safety flags.",
        ),
    ]


def step(number: int, name: str, status: str, summary: str, safety_note: str) -> dict[str, Any]:
    return {
        "stepNumber": number,
        "stepName": name,
        "stepStatus": status,
        "stepSummary": summary,
        "safetyNote": safety_note,
    }


def policy_step_status(policy_result: str) -> str:
    if policy_result == "ALLOW":
        return "READY"
    if policy_result == "ALLOW_WITH_APPROVAL":
        return "REQUIRES_APPROVAL"
    if policy_result == "DENY":
        return "BLOCKED"
    return "BLOCKED"


def approval_step_status(result: dict[str, Any]) -> str:
    if not result["approvalRequired"]:
        return "INFO"
    if result["approvalDecision"] == "approved":
        return "READY"
    if result["approvalDecision"] in {"denied", "expired"}:
        return "BLOCKED"
    return "REQUIRES_APPROVAL"


def approval_summary(result: dict[str, Any]) -> str:
    if not result["approvalRequired"]:
        return "No human approval is required for this dry-run plan."
    if result["approvalDecision"] == "approved":
        return "Approval was represented as approved for planning only."
    if result["approvalDecision"] == "denied":
        return "Approval was represented as denied, so the plan is blocked."
    if result["approvalDecision"] == "expired":
        return "Approval was represented as expired, so the plan is blocked."
    return "Approval is required before this plan could be considered ready."


def capability_step_status(capability_result: str) -> str:
    if capability_result == "PASS":
        return "READY"
    if capability_result == "WARN":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def simulation_step_status(final_result: str) -> str:
    if final_result == "SIMULATED_READY":
        return "READY"
    if final_result == "SIMULATED_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def dry_run_step_status(plan_status: str) -> str:
    if plan_status == "PLAN_READY":
        return "READY"
    if plan_status == "PLAN_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def safety_proof() -> dict[str, bool]:
    return {
        "executionAttempted": False,
        "commandExecuted": False,
        "networkContacted": False,
        "agentContacted": False,
        "filesystemMutationAttempted": False,
        "rawSecretsStored": False,
        "rawHostsStored": False,
        "rawIpsStored": False,
        "rawUrlsStored": False,
        "rawPathsStored": False,
    }


def redaction_proof() -> dict[str, bool]:
    return {
        "rawRequestIdsStored": False,
        "rawDeviceIdsStored": False,
        "rawServiceIdsStored": False,
        "rawPolicyIdsStored": False,
        "rawOperatorNamesStored": False,
        "rawEmailsStored": False,
        "rawReasonsStored": False,
        "rawParametersStored": False,
        "rawHostsStored": False,
        "rawIpsStored": False,
        "rawUrlsStored": False,
        "rawPathsStored": False,
        "rawTokensStored": False,
        "rawSecretsStored": False,
        "rawCommandJsonStored": False,
        "rawPolicyJsonStored": False,
        "rawCapabilityJsonStored": False,
        "rawAgentIdentifiersStored": False,
    }


def render_summary(plan: dict[str, Any]) -> str:
    passed = plan["planStatus"] in {"PLAN_READY", "PLAN_REQUIRES_APPROVAL"}
    safety = plan["safety"]
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Dry-Run Plan Result: {'PASS' if passed else 'FAIL'}",
        f"Plan status: {plan['planStatus']}",
        f"Final simulation result: {plan['finalSimulationResult']}",
        f"Approval required: {bool_word(plan['approvalRequired'])}",
        f"Approval decision: {plan['approvalDecision']}",
        f"Matched capability count: {plan['matchedCapabilityCount']}",
        f"Step count: {len(plan['steps'])}",
        f"Execution attempted: {bool_word(safety['executionAttempted'])}",
        f"Command executed: {bool_word(safety['commandExecuted'])}",
        f"Network contacted: {bool_word(safety['networkContacted'])}",
        f"Agent contacted: {bool_word(safety['agentContacted'])}",
        f"Filesystem mutation attempted: {bool_word(safety['filesystemMutationAttempted'])}",
        "Redacted fields stored: yes",
        f"Validation error count: {plan['validationErrorCount']}",
        f"Sensitive input blocked: {bool_word(plan['sensitiveInputBlocked'])}",
    ]
    return "\n".join(lines)


def write_runtime_json(plan: dict[str, Any], simulator: Any) -> None:
    target = safe_runtime_target(RUNTIME_PLAN, simulator)
    text = json.dumps(plan, indent=2, sort_keys=False) + "\n"
    assert_safe_output(text, simulator)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_runtime_summary(summary: str, simulator: Any) -> None:
    target = safe_runtime_target(RUNTIME_SUMMARY, simulator)
    text = summary + "\n"
    assert_safe_output(text, simulator)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def safe_runtime_target(relative_target: Path, simulator: Any) -> Path:
    target = (REPO_ROOT / relative_target).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError("runtime target outside repository") from exc
    if target.exists() and simulator.is_tracked(target):
        raise RuntimeError("refusing to overwrite tracked runtime output")
    return target


def assert_safe_output(text: str, simulator: Any) -> None:
    if simulator.scan_string(text):
        raise RuntimeError("refusing to write unsafe dry-run output")


def can_write_runtime(plan: dict[str, Any]) -> bool:
    return plan["validationErrorCount"] == 0 and not plan["sensitiveInputBlocked"]


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def short_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def exit_code(plan: dict[str, Any]) -> int:
    if plan["planStatus"] in {"PLAN_READY", "PLAN_REQUIRES_APPROVAL"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
