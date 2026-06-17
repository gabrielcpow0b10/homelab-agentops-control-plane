#!/usr/bin/env python3
"""Evaluate a validated Agent Command Contract request against local policy.

This script never executes agent commands and never contacts agents or network
services. Its normal report is intentionally redacted.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT POLICY ENGINE ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"
DECISION_ALLOW = "ALLOW"
DECISION_APPROVAL = "ALLOW_WITH_APPROVAL"
DECISION_DENY = "DENY"
RISK_ORDER = {"low": 1, "medium": 2, "high": 3}
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")

USER_PATH_PATTERN = "/" + "Users/"
HOMELAB_PATH_PATTERN = "~" + "/HomeLab"
SSH_PATTERN = "." + "ssh"
GITHUB_TOKEN_PATTERN = "ghp" + "_"
GITHUB_PAT_PATTERN = "github" + "_pat" + "_"
AWS_ACCESS_KEY_PREFIX = "AK" + "IA"
PASSWORD_ASSIGNMENT_PATTERN = "password" + "="
TOKEN_ASSIGNMENT_PATTERN = "token" + "="
API_KEY_ASSIGNMENT_PATTERN = "api" + "_key" + "="
APIKEY_ASSIGNMENT_PATTERN = "api" + "key" + "="
SECRET_ASSIGNMENT_PATTERN = "secret" + "="
PRIVATE_KEY_PATTERN = "PRIVATE " + "KEY"

SENSITIVE_RE = re.compile(
    r"("
    r"https?://|"
    r"ssh://|"
    r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b|"
    + re.escape(USER_PATH_PATTERN)
    + r"|"
    + re.escape(HOMELAB_PATH_PATTERN)
    + r"|"
    + re.escape(SSH_PATTERN)
    + r"|"
    + r"BEGIN [A-Z ]*"
    + PRIVATE_KEY_PATTERN
    + r"|"
    + re.escape(GITHUB_TOKEN_PATTERN)
    + r"[A-Za-z0-9_]+|"
    + re.escape(GITHUB_PAT_PATTERN)
    + r"[A-Za-z0-9_]+|"
    + re.escape(AWS_ACCESS_KEY_PREFIX)
    + r"[0-9A-Z]{16}|"
    + re.escape(PASSWORD_ASSIGNMENT_PATTERN[:-1])
    + r"\s*=|"
    + re.escape(TOKEN_ASSIGNMENT_PATTERN[:-1])
    + r"\s*=|"
    + r"api[_-]?key\s*=|"
    + re.escape(APIKEY_ASSIGNMENT_PATTERN[:-1])
    + r"\s*=|"
    + re.escape(SECRET_ASSIGNMENT_PATTERN[:-1])
    + r"\s*="
    r")",
    re.IGNORECASE,
)


@dataclass
class Evaluation:
    decision: str = DECISION_DENY
    policy_files_checked: int = 0
    command_files_checked: int = 0
    contract_valid: bool = False
    policy_valid: bool = False
    matching_device_count: int = 0
    allowed_action_match_count: int = 0
    denied_action_match_count: int = 0
    approval_required: bool = False
    validation_error_count: int = 0
    sensitive_input_blocked: bool = False
    validation_failures: list[str] = field(default_factory=list)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class ValidatorLoadError(ValueError):
    """Raised when the contract validator cannot be imported safely."""


def safe_repo_path(raw_path: str, input_index: int) -> Path:
    root = repo_root()
    candidate = (root / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"input[{input_index}]: refused path outside repository") from exc
    return candidate


def read_json_file(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    if SENSITIVE_RE.search(raw):
        raise ValueError("sensitive input pattern blocked")
    return json.loads(raw)


def is_safe_id(value: Any) -> bool:
    return isinstance(value, str) and bool(SAFE_ID_RE.fullmatch(value))


def is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(is_safe_id(item) for item in value)


def validate_policy(policy: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(policy, dict):
        return ["policy must be an object"]
    if policy.get("schemaVersion") != "0.6":
        errors.append("schemaVersion must be 0.6")
    if not is_safe_id(policy.get("policyId")):
        errors.append("policyId must be a safe identifier")
    if policy.get("defaultDecision") != "deny":
        errors.append("defaultDecision must be deny")
    devices = policy.get("devices")
    if not isinstance(devices, list):
        errors.append("devices must be an array")
        return errors
    for device in devices:
        if not isinstance(device, dict):
            errors.append("device policy must be an object")
            continue
        allowed_keys = {
            "deviceId",
            "allowedActions",
            "allowedServices",
            "capabilities",
            "approvalRequiredActions",
            "deniedActions",
            "maxRiskLevel",
            "enabled",
        }
        if set(device) - allowed_keys:
            errors.append("device policy has unsupported fields")
        if not is_safe_id(device.get("deviceId")):
            errors.append("deviceId must be a safe identifier")
        for key in ("allowedActions", "capabilities", "approvalRequiredActions", "deniedActions"):
            if not is_string_list(device.get(key)):
                errors.append(f"{key} must be an array of safe identifiers")
        if "allowedServices" in device and not is_string_list(device.get("allowedServices")):
            errors.append("allowedServices must be an array of safe identifiers")
        if device.get("maxRiskLevel") not in RISK_ORDER:
            errors.append("maxRiskLevel must be low, medium, or high")
        if not isinstance(device.get("enabled"), bool):
            errors.append("enabled must be a boolean")
    return errors


def load_contract_validator():
    validator_path = repo_root() / "scripts" / "validate-agent-command.py"
    if not validator_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("halo_validate_agent_command", validator_path)
    if spec is None or spec.loader is None:
        raise ValidatorLoadError("contract validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise ValidatorLoadError("contract validator import failed") from exc
    return module


def validate_command_with_contract(command_path: Path, command: Any) -> tuple[bool, int, list[str]]:
    try:
        module = load_contract_validator()
    except ValidatorLoadError as exc:
        return False, 1, [str(exc)]
    if module is not None:
        for name in ("validate_command", "validate_agent_command", "validate_contract"):
            func = getattr(module, name, None)
            if callable(func):
                result = None
                for args in ((command, 1), (command,), (command_path,)):
                    try:
                        result = func(*args)
                        break
                    except TypeError:
                        continue
                    except Exception:
                        return False, 1, ["contract validation failed"]
                else:
                    return False, 1, ["contract validation failed"]
                if isinstance(result, tuple):
                    valid = bool(result[0])
                    details = result[1] if len(result) > 1 else []
                    return valid, len(details) if isinstance(details, list) else (0 if valid else 1), []
                if isinstance(result, list):
                    return len(result) == 0, len(result), []
                if isinstance(result, bool):
                    return result, 0 if result else 1, []
    valid, error_count = validate_command_shape(command)
    return valid, error_count, []


def validate_command_shape(command: Any) -> tuple[bool, int]:
    errors = 0
    if not isinstance(command, dict):
        return False, 1
    if not is_safe_id(command.get("targetDeviceId")):
        errors += 1
    if not is_safe_id(command.get("action")):
        errors += 1
    if "targetServiceId" in command and command.get("targetServiceId") is not None:
        if not is_safe_id(command.get("targetServiceId")):
            errors += 1
    if command.get("riskLevel", "low") not in RISK_ORDER:
        errors += 1
    if "requiresApproval" in command and not isinstance(command.get("requiresApproval"), bool):
        errors += 1
    return errors == 0, errors


def command_value(command: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in command:
            return command[name]
    return default


def evaluate(policy: Any, command: Any, command_valid: bool, validation_errors: int) -> Evaluation:
    result = Evaluation(
        policy_files_checked=1,
        command_files_checked=1,
        contract_valid=command_valid,
        validation_error_count=validation_errors,
    )
    policy_errors = validate_policy(policy)
    result.policy_valid = not policy_errors
    result.validation_error_count += len(policy_errors)
    if not command_valid or policy_errors or not isinstance(command, dict):
        return result

    target_device = command_value(command, "targetDeviceId", "target_device_id")
    target_service = command_value(command, "targetServiceId", "target_service_id")
    action = command_value(command, "action")
    risk = command_value(command, "riskLevel", "risk_level", default="low")
    requires_approval = bool(command_value(command, "requiresApproval", "requires_approval", default=False))

    devices = policy.get("devices", [])
    matches = [device for device in devices if device.get("deviceId") == target_device]
    result.matching_device_count = len(matches)
    if len(matches) != 1:
        return result

    device = matches[0]
    if not device.get("enabled"):
        return result

    denied_actions = set(device.get("deniedActions", []))
    allowed_actions = set(device.get("allowedActions", []))
    approval_actions = set(device.get("approvalRequiredActions", []))
    capabilities = set(device.get("capabilities", []))

    result.denied_action_match_count = 1 if action in denied_actions else 0
    if result.denied_action_match_count:
        return result

    result.allowed_action_match_count = 1 if action in allowed_actions else 0
    if not result.allowed_action_match_count:
        return result

    if action not in capabilities:
        return result

    if target_service and "allowedServices" in device:
        if target_service not in set(device.get("allowedServices", [])):
            return result

    if RISK_ORDER.get(str(risk), 99) > RISK_ORDER.get(str(device.get("maxRiskLevel")), 0):
        return result

    result.approval_required = requires_approval or action in approval_actions
    result.decision = DECISION_APPROVAL if result.approval_required else DECISION_ALLOW
    return result


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def render_report(result: Evaluation) -> str:
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Policy Engine Result: {result.decision}",
        "",
        f"- Policy files checked: {result.policy_files_checked}",
        f"- Command files checked: {result.command_files_checked}",
        f"- Contract validation result: {bool_word(result.contract_valid)}",
        f"- Policy validation result: {bool_word(result.policy_valid)}",
        f"- Matching device policy count: {result.matching_device_count}",
        f"- Allowed action match count: {result.allowed_action_match_count}",
        f"- Denied action match count: {result.denied_action_match_count}",
        f"- Approval required: {bool_word(result.approval_required)}",
        f"- Validation error count: {result.validation_error_count}",
        f"- Sensitive input blocked: {bool_word(result.sensitive_input_blocked)}",
    ]
    for failure in result.validation_failures:
        lines.append(f"- Validation failure: {failure}")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an agent command against local policy.")
    parser.add_argument("policy", nargs="?", default="examples/agent-policy.local.example.json")
    parser.add_argument("command", nargs="?", default="examples/agent-command.health-check.example.json")
    parser.add_argument("--write-runtime-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    result = Evaluation()
    try:
        policy_path = safe_repo_path(args.policy, 1)
        command_path = safe_repo_path(args.command, 2)
        policy = read_json_file(policy_path)
        command = read_json_file(command_path)
        command_valid, command_error_count, command_failures = validate_command_with_contract(command_path, command)
        result = evaluate(policy, command, command_valid, command_error_count)
        result.validation_failures.extend(command_failures)
    except ValueError as exc:
        result.validation_error_count = 1
        result.sensitive_input_blocked = "sensitive input" in str(exc)
        result.validation_failures.append(str(exc))
    except (OSError, json.JSONDecodeError):
        result.validation_error_count = 1
        result.validation_failures.append("input could not be loaded")

    report = render_report(result)
    print(report, end="")

    if args.write_runtime_report:
        runtime_path = repo_root() / "runtime" / "agent-policy-evaluation.local.md"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(report, encoding="utf-8")

    return 0 if result.decision in {DECISION_ALLOW, DECISION_APPROVAL} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
