#!/usr/bin/env python3
"""Validate safe agent command JSON contracts without executing any action."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT COMMAND CONTRACT ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"
REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_REPORT = Path("runtime/agent-command-contract.local.md")

DEFAULT_EXAMPLES = [
    REPO_ROOT / "examples/agent-command.health-check.example.json",
    REPO_ROOT / "examples/agent-command.backup-dry-run.example.json",
    REPO_ROOT / "examples/agent-command.restart-service.requires-approval.example.json",
]

REQUIRED_FIELDS = [
    "schemaVersion",
    "requestId",
    "targetDeviceId",
    "action",
    "mode",
    "riskLevel",
    "requiresApproval",
    "dryRun",
    "requestedBy",
    "reason",
    "createdAt",
]

OPTIONAL_FIELDS = {"targetServiceId", "parameters"}
ALLOWED_FIELDS = set(REQUIRED_FIELDS) | OPTIONAL_FIELDS

ALLOWED_ACTIONS = {
    "health_check",
    "disk_status",
    "memory_status",
    "temperature_check",
    "service_status",
    "backup_dry_run",
    "backup_run",
    "security_scan",
    "log_summary",
    "restart_allowed_service",
}

BLOCKED_ACTIONS = {
    "shell_command",
    "arbitrary_command",
    "read_env",
    "read_ssh_keys",
    "read_private_key",
    "delete_files",
    "upload_private_files",
    "open_router_ports",
    "disable_firewall",
    "install_package",
    "curl_pipe_shell",
}

READ_ONLY_ACTIONS = {
    "health_check",
    "disk_status",
    "memory_status",
    "temperature_check",
    "service_status",
    "security_scan",
    "log_summary",
}

MODES = {"read_only", "dry_run", "approved_write"}
RISK_LEVELS = {"low", "medium", "high"}
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
SAFE_PARAM_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
ISO_LIKE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?$"
)

USER_PATH_PATTERN = "/" + "Users/"
HOMELAB_PATH_PATTERN = "~" + "/HomeLab"
SSH_DIR_PATTERN = r"\." + "ssh"
PRIVATE_KEY_PATTERN = "PRIVATE " + "KEY"

SENSITIVE_PATTERNS = [
    ("raw_ip", re.compile(r"(?<![A-Za-z0-9])(?:\d{1,3}\.){3}\d{1,3}(?![A-Za-z0-9])")),
    ("url", re.compile(r"\b(?:https?|ssh|ftp)://", re.IGNORECASE)),
    ("hostname_hint", re.compile(r"\b[A-Za-z0-9][A-Za-z0-9-]*(?:\.[A-Za-z0-9][A-Za-z0-9-]*)*\.[A-Za-z][A-Za-z0-9-]{1,}\b")),
    ("shell_command_shape", re.compile(r"(?:[;&|`$<>]|\\\n|\bcurl\b|\bwget\b|\bsudo\b|\bsh\b|\bbash\b)", re.IGNORECASE)),
    ("token_like", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{8,}\b", re.IGNORECASE)),
    ("aws_key_like", re.compile(r"\bA" + r"KIA[A-Z0-9]{12,}\b")),
    ("password_like", re.compile(r"\bpassword\s*=", re.IGNORECASE)),
    ("api_key_like", re.compile(r"\b(?:api_key|apikey|token|secret)\s*=", re.IGNORECASE)),
    ("private_path", re.compile(r"(?:" + re.escape(USER_PATH_PATTERN) + r"|" + re.escape(HOMELAB_PATH_PATTERN) + r"|/home/[^/\s]+/|\.\./)")),
    ("env_reference", re.compile(r"(?:^|[/\s])\.env(?:$|[/\s])", re.IGNORECASE)),
    ("ssh_key_reference", re.compile(r"(?:" + SSH_DIR_PATTERN + r"|id_" + r"rsa|id_" + r"ed25519|" + PRIVATE_KEY_PATTERN + r")", re.IGNORECASE)),
]

PARAMETER_RULES = {
    "service_status": {"serviceName"},
    "log_summary": {"logWindow"},
    "backup_dry_run": {"backupProfile"},
    "backup_run": {"backupProfile"},
    "restart_allowed_service": {"serviceName"},
}

LOG_WINDOWS = {"15m", "1h", "6h", "24h"}


@dataclass
class Report:
    checked: int = 0
    accepted: int = 0
    blocked: int = 0
    approval_required: int = 0
    read_only: int = 0
    dry_run: int = 0
    approved_write: int = 0
    sensitive_blocked: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.checked > 0 and not self.errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate safe HomeLab agent command contract JSON files."
    )
    parser.add_argument(
        "--write-runtime-report",
        action="store_true",
        help="Write the safe redacted report to runtime/agent-command-contract.local.md.",
    )
    parser.add_argument("paths", nargs="*", help="Explicit command JSON files to validate.")
    args = parser.parse_args()

    paths = [Path(path) for path in args.paths] if args.paths else DEFAULT_EXAMPLES
    report = validate_paths(paths)
    output = render_report(report)
    print(output)

    if args.write_runtime_report:
        RUNTIME_REPORT.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_REPORT.write_text(output + "\n", encoding="utf-8")
        print(f"Safe runtime report written: {RUNTIME_REPORT}")

    return 0 if report.passed else 1


def validate_paths(paths: list[Path]) -> Report:
    report = Report()
    for index, path in enumerate(paths, start=1):
        report.checked += 1
        errors, command = load_command(path, index)
        if command is not None:
            errors.extend(validate_command(command, index))

        if errors:
            report.blocked += 1
            report.errors.extend(errors)
            if any("sensitive input" in error for error in errors):
                report.sensitive_blocked = True
            continue

        report.accepted += 1
        if command and command.get("requiresApproval") is True:
            report.approval_required += 1
        mode = command.get("mode") if command else None
        if mode == "read_only":
            report.read_only += 1
        elif mode == "dry_run":
            report.dry_run += 1
        elif mode == "approved_write":
            report.approved_write += 1

    return report


def load_command(path: Path, index: int) -> tuple[list[str], dict[str, Any] | None]:
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(REPO_ROOT):
        return [f"command[{index}]: refused path outside repository"], None

    if not resolved_path.is_file():
        return [f"command[{index}]: file does not exist"], None

    try:
        text = resolved_path.read_text(encoding="utf-8")
    except OSError:
        return [f"command[{index}]: file could not be read"], None

    text_errors = scan_string(text, f"command[{index}].raw_json")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return text_errors + [f"command[{index}]: invalid JSON at line {exc.lineno}, column {exc.colno}"], None

    if not isinstance(payload, dict):
        return text_errors + [f"command[{index}]: top-level JSON value must be an object"], None

    return text_errors, payload


def validate_command(command: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    label = f"command[{index}]"

    missing = [field for field in REQUIRED_FIELDS if field not in command]
    extra = [field for field in command if field not in ALLOWED_FIELDS]
    if missing:
        errors.append(f"{label}: missing required field count {len(missing)}")
    if extra:
        errors.append(f"{label}: unexpected field count {len(extra)}")

    errors.extend(scan_value(command, label))
    errors.extend(validate_field_types(command, label))
    errors.extend(validate_enums(command, label))
    errors.extend(validate_action_rules(command, label))
    errors.extend(validate_parameters(command, label))
    return errors


def validate_field_types(command: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    for field_name in REQUIRED_FIELDS:
        if field_name not in command:
            continue
        value = command[field_name]
        if field_name in {"requiresApproval", "dryRun"}:
            if not isinstance(value, bool):
                errors.append(f"{label}.{field_name}: value must be boolean")
        elif not isinstance(value, str):
            errors.append(f"{label}.{field_name}: value must be string")

    for field_name in ("requestId", "targetDeviceId", "targetServiceId", "requestedBy"):
        value = command.get(field_name)
        if isinstance(value, str) and not SAFE_ID_RE.fullmatch(value):
            errors.append(f"{label}.{field_name}: value must be a safe identifier")

    reason = command.get("reason")
    if isinstance(reason, str):
        if not reason.strip():
            errors.append(f"{label}.reason: value must not be empty")
        if len(reason) > 160:
            errors.append(f"{label}.reason: value exceeds safe length")

    created_at = command.get("createdAt")
    if isinstance(created_at, str) and not is_iso_like(created_at):
        errors.append(f"{label}.createdAt: value must be an ISO-like timestamp")

    parameters = command.get("parameters")
    if parameters is not None and not isinstance(parameters, dict):
        errors.append(f"{label}.parameters: value must be an object")

    return errors


def validate_enums(command: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    schema_version = command.get("schemaVersion")
    if isinstance(schema_version, str) and schema_version != "0.5":
        errors.append(f"{label}.schemaVersion: unsupported value")

    action = command.get("action")
    if isinstance(action, str):
        if action in BLOCKED_ACTIONS:
            errors.append(f"{label}.action: blocked action requested")
        elif action not in ALLOWED_ACTIONS:
            errors.append(f"{label}.action: unknown action requested")

    mode = command.get("mode")
    if isinstance(mode, str) and mode not in MODES:
        errors.append(f"{label}.mode: unsupported value")

    risk_level = command.get("riskLevel")
    if isinstance(risk_level, str) and risk_level not in RISK_LEVELS:
        errors.append(f"{label}.riskLevel: unsupported value")

    return errors


def validate_action_rules(command: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    action = command.get("action")
    mode = command.get("mode")
    dry_run = command.get("dryRun")
    requires_approval = command.get("requiresApproval")
    risk_level = command.get("riskLevel")

    if action in READ_ONLY_ACTIONS:
        if mode != "read_only":
            errors.append(f"{label}: read-only action has invalid mode")
        if dry_run is not True:
            errors.append(f"{label}: read-only action must be dryRun true")
        if requires_approval is not False:
            errors.append(f"{label}: read-only action must not require approval")
    elif action == "backup_dry_run":
        if mode != "dry_run":
            errors.append(f"{label}: backup dry-run action has invalid mode")
        if dry_run is not True:
            errors.append(f"{label}: backup dry-run action must be dryRun true")
        if requires_approval is not False:
            errors.append(f"{label}: backup dry-run action must not require approval")
    elif action in {"backup_run", "restart_allowed_service"}:
        if mode != "approved_write":
            errors.append(f"{label}: approved-write action has invalid mode")
        if dry_run is not False:
            errors.append(f"{label}: approved-write action must be dryRun false")
        if requires_approval is not True:
            errors.append(f"{label}: approved-write action must require approval")
        if risk_level != "high":
            errors.append(f"{label}: approved-write action must be high risk")

    return errors


def validate_parameters(command: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    action = command.get("action")
    parameters = command.get("parameters", {})

    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        return errors

    allowed_keys = PARAMETER_RULES.get(action, set())
    keys = set(parameters)
    extra = keys - allowed_keys
    missing: set[str] = set()

    if action in PARAMETER_RULES:
        missing = allowed_keys - keys
    elif keys:
        extra = keys

    if missing:
        errors.append(f"{label}.parameters: missing allowlisted parameter count {len(missing)}")
    if extra:
        errors.append(f"{label}.parameters: unsupported parameter count {len(extra)}")

    for key, value in parameters.items():
        if not isinstance(key, str) or not SAFE_PARAM_RE.fullmatch(key):
            errors.append(f"{label}.parameters: unsafe parameter key")
        if not isinstance(value, str):
            errors.append(f"{label}.parameters.{safe_field_name(key)}: value must be string")
            continue
        if key == "logWindow":
            if value not in LOG_WINDOWS:
                errors.append(f"{label}.parameters.logWindow: unsupported value")
        elif key in {"serviceName", "backupProfile"} and not SAFE_PARAM_RE.fullmatch(value):
            errors.append(f"{label}.parameters.{key}: value must be a safe identifier")

    return errors


def scan_value(value: Any, path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, str):
        errors.extend(scan_string(value, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(scan_value(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            key_path = safe_field_name(str(key))
            errors.extend(scan_string(str(key), f"{path}.{key_path}.key"))
            errors.extend(scan_value(item, f"{path}.{key_path}"))
    return errors


def scan_string(value: str, path: str) -> list[str]:
    errors: list[str] = []
    for pattern_name, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            errors.append(f"{path}: sensitive input blocked ({pattern_name})")
    return errors


def safe_field_name(value: str) -> str:
    if SAFE_PARAM_RE.fullmatch(value):
        return value
    return "unsafe_field"


def is_iso_like(value: str) -> bool:
    if not ISO_LIKE_RE.fullmatch(value):
        return False
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def render_report(report: Report) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Command Contract Result: {status}",
        f"Total command files checked: {report.checked}",
        f"Accepted command count: {report.accepted}",
        f"Blocked command count: {report.blocked}",
        f"Approval-required command count: {report.approval_required}",
        f"Read-only command count: {report.read_only}",
        f"Dry-run command count: {report.dry_run}",
        f"Approved-write command count: {report.approved_write}",
        f"Validation error count: {len(report.errors)}",
        f"Sensitive input blocked: {'yes' if report.sensitive_blocked else 'no'}",
    ]

    if report.errors:
        lines.extend(["", "## Validation Errors"])
        for error in report.errors:
            lines.append(f"- {error}")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
