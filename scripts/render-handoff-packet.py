#!/usr/bin/env python3
"""Render a redacted agent handoff packet from the runbook preview renderer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT HANDOFF PACKET ONLY - NO EXECUTION, NO NETWORK, NO AGENT CONTACT, NO RAW SECRETS"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPABILITY = "examples/agent-capability.local.example.json"
DEFAULT_POLICY = "examples/agent-policy.local.example.json"
DEFAULT_COMMAND = "examples/agent-command.health-check.example.json"
RUNTIME_PACKET = Path("runtime/agent-handoff-packet.local.json")
RUNTIME_SUMMARY = Path("runtime/agent-handoff-packet-summary.local.md")
APPROVAL_DECISIONS = {"approved", "denied", "expired"}


class RunbookPreviewLoadError(RuntimeError):
    """Raised when the local runbook preview renderer cannot be imported."""


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    runbook_renderer = load_runbook_renderer()
    dry_run_renderer = runbook_renderer.load_dry_run_renderer()
    simulator = dry_run_renderer.load_simulator()
    packet = render_packet(args, runbook_renderer, dry_run_renderer, simulator)
    summary = render_summary(packet)
    print(summary)

    if args.write_runtime_packet or args.write_runtime_summary:
        if not can_write_runtime(packet):
            print("Runtime output blocked because input validation was not safe.")
            return 1
        try:
            if args.write_runtime_packet:
                write_runtime_json(packet, simulator)
                print("Safe runtime handoff packet written.")
            if args.write_runtime_summary:
                write_runtime_summary(summary, simulator)
                print("Safe runtime handoff summary written.")
        except RuntimeError:
            print("Runtime output blocked by safety guard.")
            return 1

    return exit_code(packet)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a safe redacted agent handoff packet.")
    parser.add_argument("paths", nargs="*", help="Optional capability registry, policy, and command JSON files.")
    parser.add_argument("--approval-decision", choices=sorted(APPROVAL_DECISIONS))
    parser.add_argument("--write-runtime-packet", action="store_true")
    parser.add_argument("--write-runtime-summary", action="store_true")
    args = parser.parse_args(argv)
    if len(args.paths) not in {0, 3}:
        parser.error("provide either no paths or exactly capability registry, policy, and command paths")
    return args


def load_runbook_renderer() -> Any:
    module_path = REPO_ROOT / "scripts" / "render-runbook-preview.py"
    spec = importlib.util.spec_from_file_location("halo_agent_runbook_preview_renderer", module_path)
    if spec is None or spec.loader is None:
        raise RunbookPreviewLoadError("runbook preview renderer could not be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise RunbookPreviewLoadError("runbook preview renderer import failed") from exc
    return module


def render_packet(
    args: argparse.Namespace,
    runbook_renderer: Any,
    dry_run_renderer: Any,
    simulator: Any,
) -> dict[str, Any]:
    paths = args.paths if args.paths else [DEFAULT_CAPABILITY, DEFAULT_POLICY, DEFAULT_COMMAND]
    preview_args = argparse.Namespace(
        paths=paths,
        approval_decision=args.approval_decision,
        write_runtime_preview=False,
        write_runtime_summary=False,
    )
    preview = runbook_renderer.render_preview(preview_args, dry_run_renderer, simulator)
    handoff_status = handoff_status_for(preview["runbookStatus"])
    created_at = simulator.utc_now()
    runbook_fingerprint = simulator.short_hash(preview)
    packet_id = "handoff_" + simulator.short_hash(
        {
            "createdAt": created_at,
            "runbookPreviewFingerprint": runbook_fingerprint,
            "handoffStatus": handoff_status,
        }
    )
    return {
        "schemaVersion": "1.3",
        "resultType": "agent_handoff_packet",
        "packetId": packet_id,
        "createdAt": created_at,
        "runbookPreviewFingerprint": runbook_fingerprint,
        "finalSimulationResult": preview["finalSimulationResult"],
        "planStatus": preview["planStatus"],
        "runbookStatus": preview["runbookStatus"],
        "handoffStatus": handoff_status,
        "handoffMode": preview["runbookMode"],
        "riskLevel": preview["riskLevel"],
        "approvalRequired": preview["approvalRequired"],
        "approvalDecision": preview["approvalDecision"],
        "matchedCapabilityCount": preview["matchedCapabilityCount"],
        "nextActorType": next_actor_type(handoff_status),
        "validationErrorCount": preview["validationErrorCount"],
        "sensitiveInputBlocked": preview["sensitiveInputBlocked"],
        "handoffChecklist": build_checklist(preview, handoff_status),
        "safety": safety_proof(),
        "redaction": redaction_proof(),
    }


def handoff_status_for(runbook_status: str) -> str:
    if runbook_status == "RUNBOOK_PREVIEW_READY":
        return "HANDOFF_READY"
    if runbook_status == "RUNBOOK_PREVIEW_REQUIRES_APPROVAL":
        return "HANDOFF_REQUIRES_APPROVAL"
    return "HANDOFF_BLOCKED"


def next_actor_type(handoff_status: str) -> str:
    if handoff_status == "HANDOFF_READY":
        return "private_agent_layer"
    if handoff_status == "HANDOFF_REQUIRES_APPROVAL":
        return "human_reviewer"
    return "none"


def build_checklist(preview: dict[str, Any], handoff_status: str) -> list[dict[str, Any]]:
    return [
        item(
            1,
            "Command Contract Confirmed",
            command_status(preview),
            "The command contract result is represented as a safe classification.",
            "Confirm that the request remains within the validated public-safe contract.",
            "Raw command JSON, request identifiers, targets, parameters, paths, URLs, hosts, IPs, tokens, and secrets are omitted.",
        ),
        item(
            2,
            "Policy Decision Confirmed",
            policy_status(preview),
            "The policy decision is carried forward only as ready, blocked, or approval-gated state.",
            "Confirm that denied or unknown policy decisions stay blocked before handoff.",
            "Raw policy content, policy identifiers, and policy rationale are omitted.",
        ),
        item(
            3,
            "Approval State Confirmed",
            approval_status(preview),
            approval_summary(preview),
            "Confirm approval state before any future private handoff attempts readiness.",
            "Reviewer identities, reason text, approval ledger details, and request details are omitted.",
        ),
        item(
            4,
            "Capability Match Confirmed",
            capability_status(preview),
            "The capability registry result is reduced to a safe matched capability count.",
            "Confirm at least one compatible capability exists before handoff readiness.",
            "Raw capability content and agent identifiers are omitted.",
        ),
        item(
            5,
            "Simulation Result Confirmed",
            simulation_status(preview),
            "The final simulation result was produced without execution, network contact, or agent contact.",
            "Use the simulation classification to decide whether handoff can remain ready.",
            "No command was executed and no network service or agent was contacted.",
        ),
        item(
            6,
            "Dry-Run Plan Confirmed",
            dry_run_status(preview),
            "The dry-run plan status is carried forward as a safe handoff classification.",
            "Confirm the plan is ready or explicitly approval-gated before reviewing handoff.",
            "Dry-run plan details are represented only by classifications and the runbook fingerprint.",
        ),
        item(
            7,
            "Runbook Preview Confirmed",
            runbook_status(preview),
            "The runbook preview is referenced by a short fingerprint for public-safe correlation.",
            "Confirm the preview status before any future private agent layer receives a packet.",
            "Runbook sections are not expanded with raw command, policy, capability, target, or reviewer data.",
        ),
        item(
            8,
            "Execution Boundary Confirmed",
            "INFO",
            "This handoff packet is a review artifact only and never crosses into execution.",
            "Keep all execution, agent contact, and network contact outside this public milestone.",
            "Safety flags confirm no execution, command, network, agent, or mutable operational target was contacted.",
        ),
        item(
            9,
            "Handoff Decision",
            handoff_item_status(handoff_status),
            handoff_summary(handoff_status),
            "Use this final state to decide whether a human reviewer or future private layer should act next.",
            "The packet contains only hashes, classifications, counts, checklist statuses, and safety confirmations.",
        ),
    ]


def item(
    number: int,
    name: str,
    status: str,
    summary: str,
    reviewer_note: str,
    safety_note: str,
) -> dict[str, Any]:
    return {
        "itemNumber": number,
        "itemName": name,
        "itemStatus": status,
        "itemSummary": summary,
        "reviewerNote": reviewer_note,
        "safetyNote": safety_note,
    }


def command_status(preview: dict[str, Any]) -> str:
    if preview["sensitiveInputBlocked"] or preview["validationErrorCount"] > 0:
        return "BLOCKED"
    return "READY"


def policy_status(preview: dict[str, Any]) -> str:
    if preview["planStatus"] == "PLAN_BLOCKED":
        return "BLOCKED"
    if preview["planStatus"] == "PLAN_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "READY"


def approval_status(preview: dict[str, Any]) -> str:
    if not preview["approvalRequired"]:
        return "INFO"
    if preview["approvalDecision"] == "approved":
        return "READY"
    if preview["approvalDecision"] in {"denied", "expired"}:
        return "BLOCKED"
    return "REQUIRES_APPROVAL"


def approval_summary(preview: dict[str, Any]) -> str:
    if not preview["approvalRequired"]:
        return "No approval decision is required for this handoff packet."
    if preview["approvalDecision"] == "approved":
        return "The approval-gated workflow is represented as approved for handoff rendering only."
    if preview["approvalDecision"] == "denied":
        return "The approval-gated workflow is blocked because the approval decision is denied."
    if preview["approvalDecision"] == "expired":
        return "The approval-gated workflow is blocked because the approval decision is expired."
    return "The workflow still requires approval, so the handoff packet remains approval-gated."


def capability_status(preview: dict[str, Any]) -> str:
    if preview["matchedCapabilityCount"] > 0 and preview["planStatus"] != "PLAN_BLOCKED":
        return "READY"
    return "BLOCKED"


def simulation_status(preview: dict[str, Any]) -> str:
    if preview["finalSimulationResult"] == "SIMULATED_READY":
        return "READY"
    if preview["finalSimulationResult"] == "SIMULATED_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def dry_run_status(preview: dict[str, Any]) -> str:
    if preview["planStatus"] == "PLAN_READY":
        return "READY"
    if preview["planStatus"] == "PLAN_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def runbook_status(preview: dict[str, Any]) -> str:
    if preview["runbookStatus"] == "RUNBOOK_PREVIEW_READY":
        return "READY"
    if preview["runbookStatus"] == "RUNBOOK_PREVIEW_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def handoff_item_status(handoff_status: str) -> str:
    if handoff_status == "HANDOFF_READY":
        return "READY"
    if handoff_status == "HANDOFF_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def handoff_summary(handoff_status: str) -> str:
    if handoff_status == "HANDOFF_READY":
        return "The handoff packet is ready for a future private agent layer or final reviewer."
    if handoff_status == "HANDOFF_REQUIRES_APPROVAL":
        return "The handoff packet is safe to review but requires approval before readiness."
    return "The handoff packet is blocked and must not be treated as ready."


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
        "rawReviewerIdentitiesStored": False,
        "rawReviewerNamesStored": False,
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


def render_summary(packet: dict[str, Any]) -> str:
    passed = packet["handoffStatus"] in {"HANDOFF_READY", "HANDOFF_REQUIRES_APPROVAL"}
    safety = packet["safety"]
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Handoff Packet Result: {'PASS' if passed else 'FAIL'}",
        f"Handoff status: {packet['handoffStatus']}",
        f"Runbook status: {packet['runbookStatus']}",
        f"Plan status: {packet['planStatus']}",
        f"Final simulation result: {packet['finalSimulationResult']}",
        f"Approval required: {bool_word(packet['approvalRequired'])}",
        f"Approval decision: {packet['approvalDecision']}",
        f"Matched capability count: {packet['matchedCapabilityCount']}",
        f"Checklist item count: {len(packet['handoffChecklist'])}",
        f"Next actor type: {packet['nextActorType']}",
        f"Execution attempted: {bool_word(safety['executionAttempted'])}",
        f"Command executed: {bool_word(safety['commandExecuted'])}",
        f"Network contacted: {bool_word(safety['networkContacted'])}",
        f"Agent contacted: {bool_word(safety['agentContacted'])}",
        f"Filesystem mutation attempted: {bool_word(safety['filesystemMutationAttempted'])}",
        "Redacted fields stored: yes",
        f"Validation error count: {packet['validationErrorCount']}",
        f"Sensitive input blocked: {bool_word(packet['sensitiveInputBlocked'])}",
    ]
    return "\n".join(lines)


def write_runtime_json(packet: dict[str, Any], simulator: Any) -> None:
    target = safe_runtime_target(RUNTIME_PACKET, simulator)
    text = json.dumps(packet, indent=2, sort_keys=False) + "\n"
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
        raise RuntimeError("refusing to write unsafe handoff packet output")


def can_write_runtime(packet: dict[str, Any]) -> bool:
    return packet["validationErrorCount"] == 0 and not packet["sensitiveInputBlocked"]


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def exit_code(packet: dict[str, Any]) -> int:
    if packet["validationErrorCount"] > 0 or packet["sensitiveInputBlocked"]:
        return 1
    if packet["handoffStatus"] in {"HANDOFF_READY", "HANDOFF_REQUIRES_APPROVAL"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
