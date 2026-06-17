#!/usr/bin/env python3
"""Record a redacted local audit event for an agent policy evaluation.

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT AUDIT LOG ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"
EVENT_TYPE = "agent_policy_evaluation"
SCHEMA_VERSION = "0.7"
RUNTIME_JSONL = Path("runtime/agent-audit.local.jsonl")
RUNTIME_SUMMARY = Path("runtime/agent-audit-summary.local.md")
ALLOWED_RUNTIME_TARGETS = {RUNTIME_JSONL, RUNTIME_SUMMARY}
HASH_RE = re.compile(r"^[a-f0-9]{16}$")
EVENT_ID_RE = re.compile(r"^audit_[a-f0-9]{16}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ACTION_CLASSES = {"read_only", "dry_run", "approved_write"}
RISK_LEVELS = {"low", "medium", "high"}
POLICY_RESULTS = {"ALLOW", "ALLOW_WITH_APPROVAL", "DENY"}


@dataclass
class AuditRun:
    generated: bool = False
    policy_result: str = "DENY"
    contract_result: str = "fail"
    approval_required: bool = False
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


def short_hash(value: Any) -> str:
    import hashlib

    if not isinstance(value, str):
        value = canonical_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


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


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_event(engine: Any, policy: dict[str, Any], command: dict[str, Any], evaluation: Any) -> dict[str, Any]:
    target_service = command.get("targetServiceId")
    created_at = utc_now()
    command_fingerprint = short_hash(command)
    policy_fingerprint = short_hash(policy)
    request_ref = short_hash(str(command.get("requestId", "")))
    target_device_ref = short_hash(str(command.get("targetDeviceId", "")))
    policy_ref = short_hash(str(policy.get("policyId", "")))
    target_service_ref = "none" if target_service in (None, "") else short_hash(str(target_service))
    event_seed = {
        "createdAt": created_at,
        "requestRefHash": request_ref,
        "targetDeviceRefHash": target_device_ref,
        "targetServiceRefHash": target_service_ref,
        "policyRefHash": policy_ref,
        "commandFingerprint": command_fingerprint,
        "policyFingerprint": policy_fingerprint,
        "policyEvaluationResult": evaluation.decision,
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "eventType": EVENT_TYPE,
        "eventId": "audit_" + short_hash(event_seed),
        "createdAt": created_at,
        "requestRefHash": request_ref,
        "targetDeviceRefHash": target_device_ref,
        "targetServiceRefHash": target_service_ref,
        "policyRefHash": policy_ref,
        "commandFingerprint": command_fingerprint,
        "policyFingerprint": policy_fingerprint,
        "actionClass": str(command.get("mode", "read_only")),
        "riskLevel": str(command.get("riskLevel", "low")),
        "contractValidationResult": "pass" if evaluation.contract_valid else "fail",
        "policyEvaluationResult": evaluation.decision,
        "approvalRequired": bool(evaluation.approval_required),
        "executionAttempted": False,
        "networkContacted": False,
        "agentContacted": False,
        "redaction": {
            "rawIdsOmitted": True,
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
        "eventId",
        "createdAt",
        "requestRefHash",
        "targetDeviceRefHash",
        "targetServiceRefHash",
        "policyRefHash",
        "commandFingerprint",
        "policyFingerprint",
        "actionClass",
        "riskLevel",
        "contractValidationResult",
        "policyEvaluationResult",
        "approvalRequired",
        "executionAttempted",
        "networkContacted",
        "agentContacted",
        "redaction",
    }
    if set(event) != required:
        errors.append("audit event field set is invalid")
    if event.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("audit event schema version is invalid")
    if event.get("eventType") != EVENT_TYPE:
        errors.append("audit event type is invalid")
    if not isinstance(event.get("eventId"), str) or not EVENT_ID_RE.fullmatch(event["eventId"]):
        errors.append("audit event id is invalid")
    if not isinstance(event.get("createdAt"), str) or not UTC_RE.fullmatch(event["createdAt"]):
        errors.append("audit event timestamp is invalid")
    for field_name in (
        "requestRefHash",
        "targetDeviceRefHash",
        "policyRefHash",
        "commandFingerprint",
        "policyFingerprint",
    ):
        if not isinstance(event.get(field_name), str) or not HASH_RE.fullmatch(event[field_name]):
            errors.append("audit event hash field is invalid")
    service_hash = event.get("targetServiceRefHash")
    if service_hash != "none" and (not isinstance(service_hash, str) or not HASH_RE.fullmatch(service_hash)):
        errors.append("audit event service hash field is invalid")
    if event.get("actionClass") not in ACTION_CLASSES:
        errors.append("audit event action class is invalid")
    if event.get("riskLevel") not in RISK_LEVELS:
        errors.append("audit event risk level is invalid")
    if event.get("contractValidationResult") not in {"pass", "fail"}:
        errors.append("audit event contract result is invalid")
    if event.get("policyEvaluationResult") not in POLICY_RESULTS:
        errors.append("audit event policy result is invalid")
    for field_name in ("approvalRequired", "executionAttempted", "networkContacted", "agentContacted"):
        if not isinstance(event.get(field_name), bool):
            errors.append("audit event boolean field is invalid")
    if event.get("executionAttempted") or event.get("networkContacted") or event.get("agentContacted"):
        errors.append("audit event attempted unsafe activity")
    redaction = event.get("redaction")
    redaction_fields = {
        "rawIdsOmitted",
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
        errors.append("audit event redaction field set is invalid")
    elif not all(value is True for value in redaction.values()):
        errors.append("audit event redaction proof is invalid")
    return errors


def raw_value_leaked(event: dict[str, Any], policy: dict[str, Any], command: dict[str, Any]) -> bool:
    event_text = canonical_json(event)
    raw_values = [
        command.get("requestId"),
        command.get("targetDeviceId"),
        command.get("targetServiceId"),
        policy.get("policyId"),
        command.get("reason"),
    ]
    parameters = command.get("parameters")
    if isinstance(parameters, dict):
        raw_values.extend(str(key) for key in parameters)
        raw_values.extend(str(value) for value in parameters.values())
    return any(isinstance(value, str) and value and value in event_text for value in raw_values)


def render_summary(run: AuditRun) -> str:
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Audit Log Result: {'PASS' if run.passed else 'FAIL'}",
        f"Audit event generated: {'yes' if run.generated else 'no'}",
        f"Policy evaluation result: {run.policy_result}",
        f"Contract validation result: {run.contract_result}",
        f"Approval required: {'yes' if run.approval_required else 'no'}",
        "Execution attempted: no",
        "Network contacted: no",
        "Agent contacted: no",
        f"Redacted fields stored: {'yes' if run.generated else 'no'}",
        f"Validation error count: {run.validation_error_count}",
        f"Sensitive input blocked: {'yes' if run.sensitive_input_blocked else 'no'}",
    ]
    for failure in run.failures:
        lines.append(f"Validation failure: {failure}")
    return "\n".join(lines) + "\n"


def write_runtime_files(args: argparse.Namespace, run: AuditRun, summary: str) -> None:
    root = repo_root()
    runtime_dir = root / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if args.append_runtime_log:
        if run.event is None:
            raise ValueError("audit event was not generated")
        jsonl_path = root / RUNTIME_JSONL
        refuse_tracked_runtime_target(jsonl_path)
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(run.event) + "\n")
    if args.write_runtime_summary:
        summary_path = root / RUNTIME_SUMMARY
        refuse_tracked_runtime_target(summary_path)
        summary_path.write_text(summary, encoding="utf-8")


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


def run_audit(args: argparse.Namespace) -> AuditRun:
    run = AuditRun()
    try:
        engine = load_policy_engine()
        policy_path = safe_repo_path(args.policy, 1)
        command_path = safe_repo_path(args.command, 2)
        policy = load_json_with_engine(engine, policy_path)
        command = load_json_with_engine(engine, command_path)
        command_valid, command_error_count, command_failures = engine.validate_command_with_contract(
            command_path, command
        )
        evaluation = engine.evaluate(policy, command, command_valid, command_error_count)
        evaluation.validation_failures.extend(command_failures)
        run.policy_result = evaluation.decision
        run.contract_result = "pass" if evaluation.contract_valid else "fail"
        run.approval_required = bool(evaluation.approval_required)
        run.validation_error_count = int(evaluation.validation_error_count)
        run.failures.extend(evaluation.validation_failures)
        if run.validation_error_count or run.failures:
            return run
        if not isinstance(policy, dict) or not isinstance(command, dict):
            run.validation_error_count = 1
            run.failures.append("input top-level value must be an object")
            return run
        event = build_event(engine, policy, command, evaluation)
        event_errors = validate_event(event)
        if raw_value_leaked(event, policy, command):
            event_errors.append("audit event contains raw input values")
        if event_errors:
            run.validation_error_count += len(event_errors)
            run.failures.extend(event_errors)
            return run
        run.event = event
        run.generated = True
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
    parser = argparse.ArgumentParser(description="Generate a redacted local agent audit event.")
    parser.add_argument("--append-runtime-log", action="store_true")
    parser.add_argument("--write-runtime-summary", action="store_true")
    parser.add_argument("policy", nargs="?", default="examples/agent-policy.local.example.json")
    parser.add_argument("command", nargs="?", default="examples/agent-command.health-check.example.json")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    run = run_audit(args)
    summary = render_summary(run)
    print(summary, end="")
    if run.passed and (args.append_runtime_log or args.write_runtime_summary):
        try:
            write_runtime_files(args, run, summary)
        except ValueError as exc:
            run.generated = False
            run.validation_error_count = 1
            run.failures.append(str(exc))
            print(render_summary(run), end="")
            return 1
    return 0 if run.passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
