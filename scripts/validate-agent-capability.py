#!/usr/bin/env python3
"""Validate a public-safe Agent Capability Registry without contacting agents."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BANNER = "SAFE AGENT CAPABILITY REGISTRY ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "examples/agent-capability.local.example.json"
RUNTIME_SUMMARY = Path("runtime/agent-capability-summary.local.md")

SCHEMA_VERSION = "0.9"
REGISTRY_TYPE = "agent_capability_registry"
GENERATED_FOR = "public_sanitized_prototype"
RISK_ORDER = {"low": 1, "medium": 2, "high": 3}
ACTION_ALIASES = {"restart_allowed_service": "restart_service"}
CAPABILITY_ACTIONS = {
    "health_check",
    "service_status",
    "backup_dry_run",
    "backup_run",
    "restart_service",
}
MODES = {"read_only", "dry_run", "approved_write"}
RUNTIMES = {"raspberry_pi", "mac_mini", "linux_server", "container", "other"}
NOTES_CLASSES = {"public_example", "planned", "other"}
SAFE_CLASS_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
SAFE_DISPLAY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{1,79}$")

USER_PATH_PATTERN = "/" + "Users/"
HOMELAB_PATH_PATTERN = "~" + "/HomeLab"
SSH_DIR_PATTERN = r"\." + "ssh"
PRIVATE_KEY_PATTERN = "PRIVATE " + "KEY"

SENSITIVE_PATTERNS = [
    ("raw_ip", re.compile(r"(?<![A-Za-z0-9])(?:\d{1,3}\.){3}\d{1,3}(?![A-Za-z0-9])")),
    ("url", re.compile(r"\b(?:https?|ssh|ftp)://", re.IGNORECASE)),
    ("hostname_hint", re.compile(r"\b[A-Za-z0-9][A-Za-z0-9-]*(?:\.[A-Za-z0-9][A-Za-z0-9-]*)*\.[A-Za-z][A-Za-z0-9-]{1,}\b")),
    ("token_like", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{8,}\b", re.IGNORECASE)),
    ("aws_key_like", re.compile(r"\bA" + r"KIA[A-Z0-9]{12,}\b")),
    ("password_like", re.compile(r"\bpassword\s*=", re.IGNORECASE)),
    ("api_key_like", re.compile(r"\b(?:api_key|apikey|token|secret)\s*=", re.IGNORECASE)),
    ("private_path", re.compile(r"(?:" + re.escape(USER_PATH_PATTERN) + r"|" + re.escape(HOMELAB_PATH_PATTERN) + r"|/home/[^/\s]+/|\.\./)")),
    ("env_reference", re.compile(r"(?:^|[/\s])\.env(?:$|[/\s])", re.IGNORECASE)),
    ("ssh_key_reference", re.compile(r"(?:" + SSH_DIR_PATTERN + r"|id_" + r"rsa|id_" + r"ed25519|" + PRIVATE_KEY_PATTERN + r")", re.IGNORECASE)),
]


@dataclass
class Result:
    registry_files_checked: int = 0
    command_files_checked: int = 0
    enabled_agent_class_count: int = 0
    disabled_agent_class_count: int = 0
    supported_action_count: int = 0
    matching_capability_count: int = 0
    denied_action_match_count: int = 0
    unsupported_mode_count: int = 0
    risk_too_high_count: int = 0
    approval_required_by_capability: bool = False
    sensitive_input_blocked: bool = False
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    runtime_summary_written: bool = False

    @property
    def status(self) -> str:
        if self.validation_errors:
            return "FAIL"
        if self.approval_required_by_capability or self.warnings:
            return "WARN"
        return "PASS"

    @property
    def ok(self) -> bool:
        return self.status in {"PASS", "WARN"}


class CommandValidatorLoadError(RuntimeError):
    """Raised when the Agent Command Contract validator cannot be imported."""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a public-safe Agent Capability Registry."
    )
    parser.add_argument(
        "--write-runtime-summary",
        action="store_true",
        help="Write a safe redacted summary to runtime/agent-capability-summary.local.md.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional registry JSON path followed by optional command JSON path.",
    )
    args = parser.parse_args()

    if len(args.paths) > 2:
        result = Result(validation_errors=["too many input files"])
        print(render_summary(result))
        return 1

    registry_path = args.paths[0] if args.paths else str(DEFAULT_REGISTRY.relative_to(REPO_ROOT))
    command_path = args.paths[1] if len(args.paths) == 2 else None

    result = validate_registry_and_command(registry_path, command_path)
    output = render_summary(result)
    print(output)

    if args.write_runtime_summary and result.ok:
        write_runtime_summary(output, result)
        print(f"Safe runtime summary written: {RUNTIME_SUMMARY}")

    return 0 if result.ok else 1


def validate_registry_and_command(registry_raw_path: str, command_raw_path: str | None) -> Result:
    result = Result()
    registry, registry_errors = load_registry(registry_raw_path, result)
    if registry_errors:
        result.validation_errors.extend(registry_errors)
        return result

    registry_errors = validate_registry(registry, result)
    if registry_errors:
        result.validation_errors.extend(registry_errors)
        return result

    if command_raw_path is None:
        return result

    command, command_errors = load_command(command_raw_path, result)
    if command_errors:
        result.validation_errors.extend(command_errors)
        return result

    match_command(registry, command, result)
    return result


def safe_repo_path(raw_path: str, input_index: int) -> Path:
    root = REPO_ROOT
    raw = Path(raw_path)
    candidate = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"input[{input_index}]: refused path outside repository") from exc
    return candidate


def load_registry(raw_path: str, result: Result) -> tuple[dict[str, Any] | None, list[str]]:
    result.registry_files_checked += 1
    try:
        path = safe_repo_path(raw_path, 1)
    except ValueError as exc:
        return None, [str(exc)]
    payload, errors = read_json(path, "registry")
    if errors:
        if any("sensitive input" in error for error in errors):
            result.sensitive_input_blocked = True
        return None, errors
    if not isinstance(payload, dict):
        return None, ["registry: top-level JSON value must be an object"]
    return payload, []


def load_command(raw_path: str, result: Result) -> tuple[dict[str, Any] | None, list[str]]:
    result.command_files_checked += 1
    try:
        path = safe_repo_path(raw_path, 2)
    except ValueError as exc:
        return None, [str(exc)]

    payload, errors = read_json(path, "command")
    if errors:
        if any("sensitive input" in error for error in errors):
            result.sensitive_input_blocked = True
        return None, errors
    if not isinstance(payload, dict):
        return None, ["command: top-level JSON value must be an object"]

    contract_errors = validate_command_with_contract(path, payload)
    if contract_errors:
        return None, ["command: Agent Command Contract validation failed"]
    return payload, []


def read_json(path: Path, label: str) -> tuple[Any | None, list[str]]:
    if not path.is_file():
        return None, [f"{label}: file does not exist"]
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None, [f"{label}: file could not be read"]
    text_errors = scan_string(raw, f"{label}.raw_json")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, text_errors + [f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno}"]
    value_errors = scan_value(payload, label)
    return payload, text_errors + value_errors


def validate_registry(registry: dict[str, Any], result: Result) -> list[str]:
    errors: list[str] = []
    allowed_top = {"schemaVersion", "registryType", "generatedFor", "agentClasses"}
    extra_top = set(registry) - allowed_top
    if extra_top:
        errors.append("registry: unsupported top-level field count")
    if registry.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("registry.schemaVersion: unsupported value")
    if registry.get("registryType") != REGISTRY_TYPE:
        errors.append("registry.registryType: unsupported value")
    if registry.get("generatedFor") != GENERATED_FOR:
        errors.append("registry.generatedFor: unsupported value")

    agent_classes = registry.get("agentClasses")
    if not isinstance(agent_classes, list) or not agent_classes:
        errors.append("registry.agentClasses: value must be a non-empty array")
        return errors

    seen_ids: set[str] = set()
    supported_actions: set[str] = set()
    for index, agent_class in enumerate(agent_classes, start=1):
        if not isinstance(agent_class, dict):
            errors.append(f"agentClass[{index}]: value must be an object")
            continue
        errors.extend(validate_agent_class(agent_class, index, seen_ids))
        if agent_class.get("enabled") is True:
            result.enabled_agent_class_count += 1
            supported_actions.update(action for action in agent_class.get("supportedActions", []) if isinstance(action, str))
        else:
            result.disabled_agent_class_count += 1

    result.supported_action_count = len(supported_actions & CAPABILITY_ACTIONS)
    if result.enabled_agent_class_count == 0:
        errors.append("registry.agentClasses: at least one enabled class is required")
    return errors


def validate_agent_class(agent_class: dict[str, Any], index: int, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    label = f"agentClass[{index}]"
    required = {
        "agentClassId",
        "displayName",
        "enabled",
        "agentRuntimeClass",
        "supportedActions",
        "supportedModes",
        "maxRiskLevel",
        "requiresApprovalForActions",
        "deniedActions",
        "safetyFlags",
        "notesClass",
    }
    extra = set(agent_class) - required
    missing = required - set(agent_class)
    if missing:
        errors.append(f"{label}: missing required field count")
    if extra:
        errors.append(f"{label}: unsupported field count")

    agent_class_id = agent_class.get("agentClassId")
    if not isinstance(agent_class_id, str) or not SAFE_CLASS_ID_RE.fullmatch(agent_class_id):
        errors.append(f"{label}.agentClassId: value must be a safe generic class id")
    elif agent_class_id in seen_ids:
        errors.append(f"{label}.agentClassId: duplicate class id")
    else:
        seen_ids.add(agent_class_id)

    display_name = agent_class.get("displayName")
    if not isinstance(display_name, str) or not SAFE_DISPLAY_RE.fullmatch(display_name):
        errors.append(f"{label}.displayName: value must be a safe generic display name")
    if not isinstance(agent_class.get("enabled"), bool):
        errors.append(f"{label}.enabled: value must be boolean")
    if agent_class.get("agentRuntimeClass") not in RUNTIMES:
        errors.append(f"{label}.agentRuntimeClass: unsupported value")
    errors.extend(validate_enum_list(agent_class, "supportedActions", CAPABILITY_ACTIONS, label))
    errors.extend(validate_enum_list(agent_class, "supportedModes", MODES, label))
    if agent_class.get("maxRiskLevel") not in RISK_ORDER:
        errors.append(f"{label}.maxRiskLevel: unsupported value")
    errors.extend(validate_enum_list(agent_class, "requiresApprovalForActions", CAPABILITY_ACTIONS, label))
    errors.extend(validate_enum_list(agent_class, "deniedActions", CAPABILITY_ACTIONS, label))
    if agent_class.get("notesClass") not in NOTES_CLASSES:
        errors.append(f"{label}.notesClass: unsupported value")
    errors.extend(validate_safety_flags(agent_class.get("safetyFlags"), label))

    supported = set(agent_class.get("supportedActions", [])) if isinstance(agent_class.get("supportedActions"), list) else set()
    approvals = set(agent_class.get("requiresApprovalForActions", [])) if isinstance(agent_class.get("requiresApprovalForActions"), list) else set()
    denied = set(agent_class.get("deniedActions", [])) if isinstance(agent_class.get("deniedActions"), list) else set()
    if approvals - supported:
        errors.append(f"{label}.requiresApprovalForActions: action must also be supported")
    if supported & denied:
        errors.append(f"{label}.deniedActions: action cannot also be supported")
    return errors


def validate_enum_list(agent_class: dict[str, Any], field_name: str, allowed: set[str], label: str) -> list[str]:
    value = agent_class.get(field_name)
    if not isinstance(value, list):
        return [f"{label}.{field_name}: value must be an array"]
    errors: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or item not in allowed:
            errors.append(f"{label}.{field_name}: unsupported value")
        elif item in seen:
            errors.append(f"{label}.{field_name}: duplicate value")
        else:
            seen.add(item)
    return errors


def validate_safety_flags(value: Any, label: str) -> list[str]:
    required = {
        "noShellExecution",
        "noArbitraryFileRead",
        "noSecretRead",
        "noNetworkScan",
        "noRawHostOutput",
        "noRawIpOutput",
        "publicSafeExample",
    }
    if not isinstance(value, dict):
        return [f"{label}.safetyFlags: value must be an object"]
    errors: list[str] = []
    if set(value) != required:
        errors.append(f"{label}.safetyFlags: required safety flags mismatch")
    for key in required:
        if value.get(key) is not True:
            errors.append(f"{label}.safetyFlags.{key}: value must be true")
    return errors


def load_command_validator() -> Any:
    validator_path = REPO_ROOT / "scripts" / "validate-agent-command.py"
    spec = importlib.util.spec_from_file_location("halo_validate_agent_command_for_capability", validator_path)
    if spec is None or spec.loader is None:
        raise CommandValidatorLoadError("command validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise CommandValidatorLoadError("command validator import failed") from exc
    return module


def validate_command_with_contract(command_path: Path, command: dict[str, Any]) -> list[str]:
    try:
        module = load_command_validator()
    except CommandValidatorLoadError as exc:
        return [str(exc)]
    errors: list[str] = []
    load_command_func = getattr(module, "load_command", None)
    validate_command_func = getattr(module, "validate_command", None)
    if callable(load_command_func):
        loaded_errors, loaded_command = load_command_func(command_path, 1)
        errors.extend(loaded_errors)
        if loaded_command is None:
            return errors or ["contract validation failed"]
        command = loaded_command
    if callable(validate_command_func):
        errors.extend(validate_command_func(command, 1))
    else:
        errors.append("contract validation failed")
    return errors


def command_action_to_capability(action: Any) -> str:
    if not isinstance(action, str):
        return ""
    return ACTION_ALIASES.get(action, action)


def match_command(registry: dict[str, Any], command: dict[str, Any], result: Result) -> None:
    action = command_action_to_capability(command.get("action"))
    mode = command.get("mode")
    risk_level = command.get("riskLevel")
    classes = registry.get("agentClasses", [])
    public_example_match_count = 0
    planned_or_limited_match_count = 0

    for agent_class in classes:
        if not isinstance(agent_class, dict) or agent_class.get("enabled") is not True:
            continue
        supported_actions = set(agent_class.get("supportedActions", []))
        denied_actions = set(agent_class.get("deniedActions", []))
        supported_modes = set(agent_class.get("supportedModes", []))

        if action in denied_actions:
            result.denied_action_match_count += 1
            continue
        if action not in supported_actions:
            continue
        if mode not in supported_modes:
            result.unsupported_mode_count += 1
            continue
        if risk_exceeds(str(risk_level), str(agent_class.get("maxRiskLevel"))):
            result.risk_too_high_count += 1
            continue

        result.matching_capability_count += 1
        if action in set(agent_class.get("requiresApprovalForActions", [])):
            result.approval_required_by_capability = True
        if agent_class.get("notesClass") in {"planned", "other"}:
            planned_or_limited_match_count += 1
        else:
            public_example_match_count += 1

    if result.denied_action_match_count:
        result.validation_errors.append("command action is denied by an enabled capability class")
    elif result.unsupported_mode_count:
        result.validation_errors.append("command mode is unsupported by matching capability classes")
    elif result.risk_too_high_count:
        result.validation_errors.append("command risk level exceeds matching capability class limit")
    elif result.matching_capability_count == 0:
        result.validation_errors.append("no enabled matching capability found for command")
    elif public_example_match_count == 0 and planned_or_limited_match_count > 0:
        result.warnings.append("only planned or limited capability matched")


def risk_exceeds(command_risk: str, max_risk: str) -> bool:
    return RISK_ORDER.get(command_risk, 99) > RISK_ORDER.get(max_risk, -1)


def scan_value(value: Any, path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, str):
        errors.extend(scan_string(value, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(scan_value(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            errors.extend(scan_string(str(key), f"{path}.field_name"))
            errors.extend(scan_value(item, f"{path}.value"))
    return errors


def scan_string(value: str, path: str) -> list[str]:
    errors: list[str] = []
    for pattern_name, pattern in SENSITIVE_PATTERNS:
        if pattern.search(value):
            errors.append(f"{path}: sensitive input blocked ({pattern_name})")
    return errors


def render_summary(result: Result) -> str:
    lines = [
        f"# {BANNER}",
        "",
        f"Agent Capability Registry Result: {result.status}",
        f"Registry files checked: {result.registry_files_checked}",
        f"Command files checked: {result.command_files_checked}",
        f"Enabled agent class count: {result.enabled_agent_class_count}",
        f"Disabled agent class count: {result.disabled_agent_class_count}",
        f"Supported action count: {result.supported_action_count}",
        f"Matching capability count: {result.matching_capability_count}",
        f"Denied action match count: {result.denied_action_match_count}",
        f"Unsupported mode count: {result.unsupported_mode_count}",
        f"Risk too high count: {result.risk_too_high_count}",
        f"Approval required by capability: {'yes' if result.approval_required_by_capability else 'no'}",
        f"Validation error count: {len(result.validation_errors)}",
        f"Sensitive input blocked: {'yes' if result.sensitive_input_blocked else 'no'}",
        "Execution attempted: no",
        "Network contacted: no",
        "Agent contacted: no",
    ]
    if result.warnings and not result.validation_errors:
        lines.extend(["", "## Warnings"])
        for warning in sorted(set(result.warnings)):
            lines.append(f"- {warning}")
    if result.validation_errors:
        lines.extend(["", "## Validation Errors"])
        for error in result.validation_errors:
            lines.append(f"- {error}")
    return "\n".join(lines)


def write_runtime_summary(output: str, result: Result) -> None:
    target = (REPO_ROOT / RUNTIME_SUMMARY).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError("runtime summary target outside repository") from exc
    if target.exists() and is_tracked(target):
        raise RuntimeError("refusing to overwrite tracked runtime summary")
    if scan_string(output, "runtime_summary"):
        raise RuntimeError("refusing to write unsafe runtime summary")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output + "\n", encoding="utf-8")
    result.runtime_summary_written = True


def is_tracked(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError("refusing tracked check for path outside repository") from exc

    index_path = REPO_ROOT / ".git" / "index"
    try:
        index_bytes = index_path.read_bytes()
    except OSError:
        return False

    return git_index_contains_path(index_bytes, relative.as_posix())


def git_index_contains_path(index_bytes: bytes, relative_path: str) -> bool:
    wanted = relative_path.encode("utf-8")
    if len(index_bytes) < 12 or index_bytes[:4] != b"DIRC":
        return wanted in index_bytes

    version = int.from_bytes(index_bytes[4:8], "big")
    entry_count = int.from_bytes(index_bytes[8:12], "big")
    if version not in {2, 3}:
        return wanted in index_bytes

    offset = 12
    for _ in range(entry_count):
        if offset + 62 > len(index_bytes):
            return wanted in index_bytes
        path_start = offset + 62
        path_end = index_bytes.find(b"\x00", path_start)
        if path_end == -1:
            return wanted in index_bytes
        if index_bytes[path_start:path_end] == wanted:
            return True
        entry_len = path_end - offset + 1
        offset += entry_len + ((8 - (entry_len % 8)) % 8)
    return False


if __name__ == "__main__":
    sys.exit(main())
