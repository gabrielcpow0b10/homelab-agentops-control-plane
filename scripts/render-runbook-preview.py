#!/usr/bin/env python3
"""Render a redacted agent runbook preview from the dry-run plan renderer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT RUNBOOK PREVIEW ONLY - NO EXECUTION, NO NETWORK, NO AGENT CONTACT, NO RAW SECRETS"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPABILITY = "examples/agent-capability.local.example.json"
DEFAULT_POLICY = "examples/agent-policy.local.example.json"
DEFAULT_COMMAND = "examples/agent-command.health-check.example.json"
RUNTIME_PREVIEW = Path("runtime/agent-runbook-preview.local.json")
RUNTIME_SUMMARY = Path("runtime/agent-runbook-preview-summary.local.md")
APPROVAL_DECISIONS = {"approved", "denied", "expired"}


class DryRunRendererLoadError(RuntimeError):
    """Raised when the local dry-run renderer cannot be imported."""


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    dry_run_renderer = load_dry_run_renderer()
    simulator = dry_run_renderer.load_simulator()
    preview = render_preview(args, dry_run_renderer, simulator)
    summary = render_summary(preview)
    print(summary)

    if args.write_runtime_preview or args.write_runtime_summary:
        if not can_write_runtime(preview):
            print("Runtime output blocked because input validation was not safe.")
            return 1
        try:
            if args.write_runtime_preview:
                write_runtime_json(preview, simulator)
                print("Safe runtime runbook preview written.")
            if args.write_runtime_summary:
                write_runtime_summary(summary, simulator)
                print("Safe runtime runbook summary written.")
        except RuntimeError:
            print("Runtime output blocked by safety guard.")
            return 1

    return exit_code(preview)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a safe redacted agent runbook preview.")
    parser.add_argument("paths", nargs="*", help="Optional capability registry, policy, and command JSON files.")
    parser.add_argument("--approval-decision", choices=sorted(APPROVAL_DECISIONS))
    parser.add_argument("--write-runtime-preview", action="store_true")
    parser.add_argument("--write-runtime-summary", action="store_true")
    args = parser.parse_args(argv)
    if len(args.paths) not in {0, 3}:
        parser.error("provide either no paths or exactly capability registry, policy, and command paths")
    return args


def load_dry_run_renderer() -> Any:
    module_path = REPO_ROOT / "scripts" / "render-dry-run-plan.py"
    spec = importlib.util.spec_from_file_location("halo_agent_dry_run_plan_renderer", module_path)
    if spec is None or spec.loader is None:
        raise DryRunRendererLoadError("dry-run renderer could not be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise DryRunRendererLoadError("dry-run renderer import failed") from exc
    return module


def render_preview(args: argparse.Namespace, dry_run_renderer: Any, simulator: Any) -> dict[str, Any]:
    paths = args.paths if args.paths else [DEFAULT_CAPABILITY, DEFAULT_POLICY, DEFAULT_COMMAND]
    plan_args = argparse.Namespace(
        paths=paths,
        approval_decision=args.approval_decision,
        write_runtime_plan=False,
        write_runtime_summary=False,
    )
    dry_run_plan = dry_run_renderer.render_plan(plan_args, simulator)
    plan_status = dry_run_plan["planStatus"]
    runbook_status = runbook_status_for(plan_status)
    created_at = simulator.utc_now()
    dry_run_fingerprint = simulator.short_hash(dry_run_plan)
    preview_id = "runbook_" + simulator.short_hash(
        {
            "createdAt": created_at,
            "dryRunPlanFingerprint": dry_run_fingerprint,
            "runbookStatus": runbook_status,
        }
    )
    return {
        "schemaVersion": "1.2",
        "resultType": "agent_runbook_preview",
        "previewId": preview_id,
        "createdAt": created_at,
        "dryRunPlanFingerprint": dry_run_fingerprint,
        "finalSimulationResult": dry_run_plan["finalSimulationResult"],
        "planStatus": plan_status,
        "runbookStatus": runbook_status,
        "runbookMode": dry_run_plan["planMode"],
        "riskLevel": dry_run_plan["riskLevel"],
        "approvalRequired": dry_run_plan["approvalRequired"],
        "approvalDecision": dry_run_plan["approvalDecision"],
        "matchedCapabilityCount": dry_run_plan["matchedCapabilityCount"],
        "validationErrorCount": dry_run_plan["validationErrorCount"],
        "sensitiveInputBlocked": dry_run_plan["sensitiveInputBlocked"],
        "sections": build_sections(dry_run_plan, runbook_status),
        "safety": safety_proof(),
        "redaction": redaction_proof(),
    }


def runbook_status_for(plan_status: str) -> str:
    if plan_status == "PLAN_READY":
        return "RUNBOOK_PREVIEW_READY"
    if plan_status == "PLAN_REQUIRES_APPROVAL":
        return "RUNBOOK_PREVIEW_REQUIRES_APPROVAL"
    return "RUNBOOK_PREVIEW_BLOCKED"


def build_sections(plan: dict[str, Any], runbook_status: str) -> list[dict[str, Any]]:
    return [
        section(
            1,
            "Reviewer Review",
            reviewer_review_status(plan),
            "The reviewer receives a redacted summary of the proposed agent workflow.",
            "Review classifications, approval state, and safety boundaries before any future handoff.",
            "No reason text, request identifier, or target identifier is stored.",
        ),
        section(
            2,
            "Command Safety",
            command_safety_status(plan),
            "The command contract result is represented only as a safe plan classification.",
            "Unsafe requests stay blocked before a runbook preview can be considered ready.",
            "Raw command JSON, parameters, paths, URLs, hosts, IPs, tokens, and secrets are omitted.",
        ),
        section(
            3,
            "Policy Decision",
            policy_section_status(plan),
            "The default-deny policy outcome is summarized as ready, blocked, or approval-gated.",
            "Policy denial prevents a ready runbook preview.",
            "Raw policy content, policy identifiers, and private policy rationale are omitted.",
        ),
        section(
            4,
            "Approval State",
            approval_section_status(plan),
            approval_section_summary(plan),
            "Approval is represented as a local dry-run classification only.",
            "Approval ledger content, reason text, and request details are omitted.",
        ),
        section(
            5,
            "Capability Match",
            capability_section_status(plan),
            "The capability registry result is reduced to a matched capability count and readiness state.",
            "A missing or incompatible capability keeps the preview blocked.",
            "Raw capability content and agent identifiers are omitted.",
        ),
        section(
            6,
            "Dry-Run Plan",
            dry_run_section_status(plan),
            "The existing dry-run plan is referenced by a short fingerprint for public-safe correlation.",
            "Only the dry-run plan status and fingerprint are carried into this preview.",
            "Dry-run steps are not expanded with raw command, policy, capability, or target details.",
        ),
        section(
            7,
            "Execution Boundary",
            "INFO",
            "This preview is a review artifact only and never crosses into execution.",
            "Keep execution, network contact, and agent contact outside this public milestone.",
            "Safety flags confirm that no command, network service, agent, or mutable filesystem target was contacted.",
        ),
        section(
            8,
            "Final Runbook Preview",
            final_section_status(runbook_status),
            final_section_summary(runbook_status),
            "Use the final status to decide whether a future private handoff could proceed.",
            "The preview contains only hashes, classifications, counts, section statuses, and safety confirmations.",
        ),
    ]


def section(
    number: int,
    name: str,
    status: str,
    summary: str,
    reviewer_note: str,
    safety_note: str,
) -> dict[str, Any]:
    return {
        "sectionNumber": number,
        "sectionName": name,
        "sectionStatus": status,
        "sectionSummary": summary,
        "reviewerNote": reviewer_note,
        "safetyNote": safety_note,
    }


def reviewer_review_status(plan: dict[str, Any]) -> str:
    if plan["sensitiveInputBlocked"] or plan["validationErrorCount"] > 0:
        return "BLOCKED"
    if plan["approvalRequired"] and plan["approvalDecision"] == "none":
        return "REQUIRES_APPROVAL"
    return "READY"


def command_safety_status(plan: dict[str, Any]) -> str:
    if plan["sensitiveInputBlocked"] or plan["validationErrorCount"] > 0:
        return "BLOCKED"
    return "READY"


def policy_section_status(plan: dict[str, Any]) -> str:
    if plan["planStatus"] == "PLAN_BLOCKED":
        return "BLOCKED"
    if plan["planStatus"] == "PLAN_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "READY"


def approval_section_status(plan: dict[str, Any]) -> str:
    if not plan["approvalRequired"]:
        return "INFO"
    if plan["approvalDecision"] == "approved":
        return "READY"
    if plan["approvalDecision"] in {"denied", "expired"}:
        return "BLOCKED"
    return "REQUIRES_APPROVAL"


def approval_section_summary(plan: dict[str, Any]) -> str:
    if not plan["approvalRequired"]:
        return "The dry-run plan does not require a human approval decision."
    if plan["approvalDecision"] == "approved":
        return "The approval-gated workflow is represented as approved for preview rendering only."
    if plan["approvalDecision"] == "denied":
        return "The approval-gated workflow is blocked because the approval decision is denied."
    if plan["approvalDecision"] == "expired":
        return "The approval-gated workflow is blocked because the approval decision is expired."
    return "The workflow still requires approval, so the preview remains approval-gated."


def capability_section_status(plan: dict[str, Any]) -> str:
    if plan["matchedCapabilityCount"] > 0 and plan["planStatus"] != "PLAN_BLOCKED":
        return "READY"
    return "BLOCKED"


def dry_run_section_status(plan: dict[str, Any]) -> str:
    if plan["planStatus"] == "PLAN_READY":
        return "READY"
    if plan["planStatus"] == "PLAN_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def final_section_status(runbook_status: str) -> str:
    if runbook_status == "RUNBOOK_PREVIEW_READY":
        return "READY"
    if runbook_status == "RUNBOOK_PREVIEW_REQUIRES_APPROVAL":
        return "REQUIRES_APPROVAL"
    return "BLOCKED"


def final_section_summary(runbook_status: str) -> str:
    if runbook_status == "RUNBOOK_PREVIEW_READY":
        return "The runbook preview is ready for human review in this public-safe model."
    if runbook_status == "RUNBOOK_PREVIEW_REQUIRES_APPROVAL":
        return "The runbook preview is safe to review but remains blocked from readiness until approval exists."
    return "The runbook preview is blocked and must not be used as a ready operational runbook."


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


def render_summary(preview: dict[str, Any]) -> str:
    passed = preview["runbookStatus"] in {"RUNBOOK_PREVIEW_READY", "RUNBOOK_PREVIEW_REQUIRES_APPROVAL"}
    safety = preview["safety"]
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Runbook Preview Result: {'PASS' if passed else 'FAIL'}",
        f"Runbook status: {preview['runbookStatus']}",
        f"Plan status: {preview['planStatus']}",
        f"Final simulation result: {preview['finalSimulationResult']}",
        f"Approval required: {bool_word(preview['approvalRequired'])}",
        f"Approval decision: {preview['approvalDecision']}",
        f"Matched capability count: {preview['matchedCapabilityCount']}",
        f"Section count: {len(preview['sections'])}",
        f"Execution attempted: {bool_word(safety['executionAttempted'])}",
        f"Command executed: {bool_word(safety['commandExecuted'])}",
        f"Network contacted: {bool_word(safety['networkContacted'])}",
        f"Agent contacted: {bool_word(safety['agentContacted'])}",
        f"Filesystem mutation attempted: {bool_word(safety['filesystemMutationAttempted'])}",
        "Redacted fields stored: yes",
        f"Validation error count: {preview['validationErrorCount']}",
        f"Sensitive input blocked: {bool_word(preview['sensitiveInputBlocked'])}",
    ]
    return "\n".join(lines)


def write_runtime_json(preview: dict[str, Any], simulator: Any) -> None:
    target = safe_runtime_target(RUNTIME_PREVIEW, simulator)
    text = json.dumps(preview, indent=2, sort_keys=False) + "\n"
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
        raise RuntimeError("refusing to write unsafe runbook preview output")


def can_write_runtime(preview: dict[str, Any]) -> bool:
    return preview["validationErrorCount"] == 0 and not preview["sensitiveInputBlocked"]


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def exit_code(preview: dict[str, Any]) -> int:
    if preview["validationErrorCount"] > 0 or preview["sensitiveInputBlocked"]:
        return 1
    if preview["runbookStatus"] in {"RUNBOOK_PREVIEW_READY", "RUNBOOK_PREVIEW_REQUIRES_APPROVAL"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
