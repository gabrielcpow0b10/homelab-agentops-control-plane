#!/usr/bin/env python3
"""Record a redacted local approval decision for an agent policy evaluation.

This milestone never executes agent commands and never contacts agents or
network services. The generated event stores hashes and classifications only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT APPROVAL LEDGER ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"
EVENT_TYPE = "agent_approval_decision"
SCHEMA_VERSION = "0.8"
RUNTIME_JSONL = Path("runtime/agent-approval-ledger.local.jsonl")
RUNTIME_SUMMARY = Path("runtime/agent-approval-summary.local.md")
ALLOWED_RUNTIME_TARGETS = {RUNTIME_JSONL, RUNTIME_SUMMARY}
APPROVAL_DECISIONS = {"approved", "denied", "expired"}
APPROVAL_REASON_CLASSES = {"routine_maintenance", "recovery", "validation", "other"}
APPROVAL_SCOPE = "single_request"
SAFE_OPERATOR_REF = "operator_local_approval_ref"
HASH_RE = re.compile(r"^[a-f0-9]{16}$")
EVENT_ID_RE = re.compile(r"^approval_[a-f0-9]{16}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ACTION_CLASSES = {"read_only", "dry_run", "approved_write"}
RISK_LEVELS = {"low", "medium", "high"}
POLICY_RESULTS = {"ALLOW", "ALLOW_WITH_APPROVAL", "DENY"}


@dataclass
class ApprovalRun:
    generated: bool = False
    policy_result: str = "DENY"
    approval_required: bool = False
    approval_decision: str = "approved"
    execution_authorized: bool = False
    validation_error_count: int = 0
    sensitive_input_blocked: bool = False
    failures: list[str] = field(default_factory=list)
    event: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return self.generated and self.event is not None and not self.failures


class PolicyEngineLoadError(RuntimeError):
    """Raised when the local policy evaluator cannot be imported."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def short_hash(value: Any) -> str:
    import hashlib

    if not isinstance(value, str):
        value = canonical_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def safe_repo_path(raw_path: str, input_index: int) -> Path:
    root = repo_root()
    candidate = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"input[{input_index}]: refused path outside repository") from exc
    return candidate


def load_policy_engine():
    engine_path = repo_root() / "scripts" / "evaluate-agent-policy.py"
    spec = importlib.util.spec_from_file_location("halo_evaluate_agent_policy", engine_path)
    if spec is None or spec.loader is None:
        raise PolicyEngineLoadError("policy evaluation import failed")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise PolicyEngineLoadError("policy evaluation import failed") from exc
    return module


def load_json_with_engine(engine: Any, path: Path) -> Any:
    return engine.read_json_file(path)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def execution_authorized(policy_result: str, approval_required: bool, approval_decision: str) -> bool:
    if approval_decision != "approved":
        return False
    if policy_result == "DENY":
        return False
    if policy_result == "ALLOW_WITH_APPROVAL":
        return approval_required
    if policy_result == "ALLOW":
        return not approval_required
    return False


def build_event(
    policy: dict[str, Any],
    command: dict[str, Any],
    evaluation: Any,
    approval_decision: str,
) -> dict[str, Any]:
    target_service = command.get("targetServiceId")
    created_at_dt = utc_now()
    created_at = format_utc(created_at_dt)
    expires_at = format_utc(created_at_dt + timedelta(hours=1)) if approval_decision == "approved" else "none"
    command_fingerprint = short_hash(command)
    policy_fingerprint = short_hash(policy)
    request_ref = short_hash(str(command.get("requestId", "")))
    target_device_ref = short_hash(str(command.get("targetDeviceId", "")))
    policy_ref = short_hash(str(policy.get("policyId", "")))
    target_service_ref = "none" if target_service in (None, "") else short_hash(str(target_service))
    authorized = execution_authorized(evaluation.decision, bool(evaluation.approval_required), approval_decision)
    event_seed = {
        "createdAt": created_at,
        "requestRefHash": request_ref,
        "targetDeviceRefHash": target_device_ref,
        "targetServiceRefHash": target_service_ref,
        "policyRefHash": policy_ref,
        "commandFingerprint": command_fingerprint,
        "policyFingerprint": policy_fingerprint,
        "policyEvaluationResult": evaluation.decision,
        "approvalDecision": approval_decision,
        "executionAuthorized": authorized,
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventType": EVENT_TYPE,
        "approvalEventId": "approval_" + short_hash(event_seed),
        "createdAt": created_at,
        "requestRefHash": request_ref,
        "targetDeviceRefHash": target_device_ref,
        "targetServiceRefHash": target_service_ref,
        "policyRefHash": policy_ref,
        "commandFingerprint": command_fingerprint,
        "policyFingerprint": policy_fingerprint,
        "actionClass": str(command.get("mode", "read_only")),
        "riskLevel": str(command.get("riskLevel", "low")),
        "policyEvaluationResult": evaluation.decision,
        "approvalRequired": bool(evaluation.approval_required),
        "approvalDecision": approval_decision,
        "approvalScope": APPROVAL_SCOPE,
        "approvedByRefHash": short_hash(SAFE_OPERATOR_REF),
        "approvalReasonClass": "routine_maintenance",
        "expiresAt": expires_at,
        "executionAuthorized": authorized,
        "executionAttempted": False,
        "networkContacted": False,
        "agentContacted": False,
        "redaction": {
            "rawIdsOmitted": True,
            "rawNamesOmitted": True,
            "rawEmailsOmitted": True,
            "rawReasonsOmitted": True,
            "rawParametersOmitted": True,
            "rawPathsOmitted": True,
            "rawHostsOmitted": True,
            "rawIpsOmitted": True,
            "rawUrlsOmitted": True,
            "rawTokensOmitted": True,
            "rawSecretsOmitted": True,
            "rawCommandJsonOmitted": True,
            "rawPolicyJsonOmitted": True,
        },
    }


def validate_event(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schemaVersion",
        "eventType",
        "approvalEventId",
        "createdAt",
        "requestRefHash",
        "targetDeviceRefHash",
        "targetServiceRefHash",
        "policyRefHash",
        "commandFingerprint",
        "policyFingerprint",
        "actionClass",
        "riskLevel",
        "policyEvaluationResult",
        "approvalRequired",
        "approvalDecision",
        "approvalScope",
        "approvedByRefHash",
        "approvalReasonClass",
        "expiresAt",
        "executionAuthorized",
        "executionAttempted",
        "networkContacted",
        "agentContacted",
        "redaction",
    }
    if set(event) != required:
        errors.append("approval event field set is invalid")
    if event.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("approval event schema version is invalid")
    if event.get("eventType") != EVENT_TYPE:
        errors.append("approval event type is invalid")
    if not isinstance(event.get("approvalEventId"), str) or not EVENT_ID_RE.fullmatch(event["approvalEventId"]):
        errors.append("approval event id is invalid")
    if not isinstance(event.get("createdAt"), str) or not UTC_RE.fullmatch(event["createdAt"]):
        errors.append("approval event timestamp is invalid")
    for field_name in (
        "requestRefHash",
        "targetDeviceRefHash",
        "policyRefHash",
        "commandFingerprint",
        "policyFingerprint",
        "approvedByRefHash",
    ):
        if not isinstance(event.get(field_name), str) or not HASH_RE.fullmatch(event[field_name]):
            errors.append("approval event hash field is invalid")
    service_hash = event.get("targetServiceRefHash")
    if service_hash != "none" and (not isinstance(service_hash, str) or not HASH_RE.fullmatch(service_hash)):
        errors.append("approval event service hash field is invalid")
    if event.get("actionClass") not in ACTION_CLASSES:
        errors.append("approval event action class is invalid")
    if event.get("riskLevel") not in RISK_LEVELS:
        errors.append("approval event risk level is invalid")
    if event.get("policyEvaluationResult") not in POLICY_RESULTS:
        errors.append("approval event policy result is invalid")
    if not isinstance(event.get("approvalRequired"), bool):
        errors.append("approval event approval required field is invalid")
    if event.get("approvalDecision") not in APPROVAL_DECISIONS:
        errors.append("approval event decision is invalid")
    if event.get("approvalScope") != APPROVAL_SCOPE:
        errors.append("approval event scope is invalid")
    if event.get("approvalReasonClass") not in APPROVAL_REASON_CLASSES:
        errors.append("approval event reason class is invalid")
    expires_at = event.get("expiresAt")
    if expires_at != "none" and (not isinstance(expires_at, str) or not UTC_RE.fullmatch(expires_at)):
        errors.append("approval event expiry is invalid")
    for field_name in ("executionAuthorized", "executionAttempted", "networkContacted", "agentContacted"):
        if not isinstance(event.get(field_name), bool):
            errors.append("approval event boolean field is invalid")
    if event.get("executionAttempted") or event.get("networkContacted") or event.get("agentContacted"):
        errors.append("approval event attempted unsafe activity")
    redaction = event.get("redaction")
    redaction_fields = {
        "rawIdsOmitted",
        "rawNamesOmitted",
        "rawEmailsOmitted",
        "rawReasonsOmitted",
        "rawParametersOmitted",
        "rawPathsOmitted",
        "rawHostsOmitted",
        "rawIpsOmitted",
        "rawUrlsOmitted",
        "rawTokensOmitted",
        "rawSecretsOmitted",
        "rawCommandJsonOmitted",
        "rawPolicyJsonOmitted",
    }
    if not isinstance(redaction, dict) or set(redaction) != redaction_fields:
        errors.append("approval event redaction field set is invalid")
    elif not all(value is True for value in redaction.values()):
        errors.append("approval event redaction proof is invalid")
    return errors


def raw_value_leaked(event: dict[str, Any], policy: dict[str, Any], command: dict[str, Any]) -> bool:
    event_text = canonical_json(event)
    raw_values = [
        command.get("requestId"),
        command.get("targetDeviceId"),
        command.get("targetServiceId"),
        command.get("requestedBy"),
        command.get("reason"),
        policy.get("policyId"),
    ]
    parameters = command.get("parameters")
    if isinstance(parameters, dict):
        raw_values.extend(str(key) for key in parameters)
        raw_values.extend(str(value) for value in parameters.values())
    return any(isinstance(value, str) and value and value in event_text for value in raw_values)


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def render_summary(run: ApprovalRun) -> str:
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Approval Ledger Result: {'PASS' if run.passed else 'FAIL'}",
        f"Approval event generated: {bool_word(run.generated)}",
        f"Policy evaluation result: {run.policy_result}",
        f"Approval required: {bool_word(run.approval_required)}",
        f"Approval decision: {run.approval_decision}",
        f"Execution authorized: {bool_word(run.execution_authorized)}",
        "Execution attempted: no",
        "Network contacted: no",
        "Agent contacted: no",
        f"Redacted fields stored: {bool_word(run.generated)}",
        f"Validation error count: {run.validation_error_count}",
        f"Sensitive input blocked: {bool_word(run.sensitive_input_blocked)}",
    ]
    for failure in run.failures:
        lines.append(f"Validation failure: {failure}")
    return "\n".join(lines) + "\n"


def refuse_tracked_runtime_target(path: Path) -> None:
    root = repo_root().resolve()
    candidate = path if path.is_absolute() else root / path
    try:
        lexical_relative = candidate.absolute().relative_to(root)
    except ValueError:
        lexical_relative = None
    if lexical_relative is not None:
        current = root
        for part in lexical_relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("runtime target uses a symlink")

    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("runtime target is outside repository") from exc

    if relative not in ALLOWED_RUNTIME_TARGETS:
        raise ValueError("runtime target is not allowed")

    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("runtime target uses a symlink")

    index_path = root / ".git" / "index"
    relative_bytes = relative.as_posix().encode("utf-8")
    try:
        index_bytes = index_path.read_bytes()
    except OSError:
        return
    if relative_bytes in index_bytes:
        raise ValueError("runtime target is tracked")


def write_runtime_files(args: argparse.Namespace, run: ApprovalRun, summary: str) -> None:
    root = repo_root()
    runtime_dir = root / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if args.append_runtime_ledger:
        if run.event is None:
            raise ValueError("approval event was not generated")
        jsonl_path = root / RUNTIME_JSONL
        refuse_tracked_runtime_target(jsonl_path)
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(run.event) + "\n")
    if args.write_runtime_summary:
        summary_path = root / RUNTIME_SUMMARY
        refuse_tracked_runtime_target(summary_path)
        summary_path.write_text(summary, encoding="utf-8")


def run_approval(args: argparse.Namespace) -> ApprovalRun:
    run = ApprovalRun(approval_decision=args.approval_decision)
    try:
        if args.approval_decision not in APPROVAL_DECISIONS:
            run.validation_error_count = 1
            run.failures.append("approval decision is invalid")
            return run
        engine = load_policy_engine()
        policy_path = safe_repo_path(args.policy, 1)
        command_path = safe_repo_path(args.command, 2)
        policy = load_json_with_engine(engine, policy_path)
        command = load_json_with_engine(engine, command_path)
        command_valid, command_error_count, command_failures = engine.validate_command_with_contract(command)
        evaluation = engine.evaluate(policy, command, command_valid, command_error_count)
        evaluation.validation_failures.extend(command_failures)
        run.policy_result = evaluation.decision
        run.approval_required = bool(evaluation.approval_required)
        run.validation_error_count = int(evaluation.validation_error_count)
        run.failures.extend(evaluation.validation_failures)
        if run.validation_error_count or run.failures:
            return run
        if not isinstance(policy, dict) or not isinstance(command, dict):
            run.validation_error_count = 1
            run.failures.append("input top-level value must be an object")
            return run
        event = build_event(policy, command, evaluation, args.approval_decision)
        event_errors = validate_event(event)
        if raw_value_leaked(event, policy, command):
            event_errors.append("approval event contains raw input values")
        if event_errors:
            run.validation_error_count += len(event_errors)
            run.failures.extend(event_errors)
            return run
        run.event = event
        run.generated = True
        run.execution_authorized = bool(event["executionAuthorized"])
    except PolicyEngineLoadError as exc:
        run.validation_error_count = 1
        run.failures.append(str(exc))
    except ValueError as exc:
        run.validation_error_count = 1
        run.sensitive_input_blocked = "sensitive input" in str(exc)
        run.failures.append(str(exc))
    except (OSError, json.JSONDecodeError):
        run.validation_error_count = 1
        run.failures.append("input could not be safely loaded")
    return run


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a redacted local agent approval event.")
    parser.add_argument("--append-runtime-ledger", action="store_true")
    parser.add_argument("--write-runtime-summary", action="store_true")
    parser.add_argument("policy", nargs="?", default="examples/agent-policy.local.example.json")
    parser.add_argument(
        "command",
        nargs="?",
        default="examples/agent-command.restart-service.requires-approval.example.json",
    )
    parser.add_argument("approval_decision", nargs="?", default="approved")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    run = run_approval(args)
    summary = render_summary(run)
    print(summary, end="")
    if run.passed and (args.append_runtime_ledger or args.write_runtime_summary):
        try:
            write_runtime_files(args, run, summary)
        except ValueError as exc:
            run.generated = False
            run.execution_authorized = False
            run.validation_error_count = 1
            run.failures.append(str(exc))
            print(render_summary(run), end="")
            return 1
    return 0 if run.passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
