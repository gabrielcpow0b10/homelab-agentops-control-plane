#!/usr/bin/env python3
"""Run a safe read-only simulation of the future agent decision pipeline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BANNER = "SAFE READ-ONLY AGENT SIMULATOR ONLY - NO EXECUTION, NO NETWORK, NO AGENT CONTACT, NO RAW SECRETS"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPABILITY = "examples/agent-capability.local.example.json"
DEFAULT_POLICY = "examples/agent-policy.local.example.json"
DEFAULT_COMMAND = "examples/agent-command.health-check.example.json"
RUNTIME_RESULT = Path("runtime/agent-simulation-result.local.json")
RUNTIME_SUMMARY = Path("runtime/agent-simulation-summary.local.md")
APPROVAL_DECISIONS = {"approved", "denied", "expired"}
ACTION_CLASSES = {"read_only", "dry_run", "approved_write"}
RISK_LEVELS = {"low", "medium", "high"}
POLICY_RESULTS = {"ALLOW", "ALLOW_WITH_APPROVAL", "DENY", "UNKNOWN"}
CAPABILITY_RESULTS = {"PASS", "WARN", "FAIL", "UNKNOWN"}
FINAL_RESULTS = {
    "SIMULATED_READY",
    "SIMULATED_BLOCKED",
    "SIMULATED_REQUIRES_APPROVAL",
}

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
    ("shell_command_shape", re.compile(r"(?:[;&|`$<>]|\\\n|\bcurl\b|\bwget\b|\bsudo\b|\bsh\b|\bbash\b)", re.IGNORECASE)),
]


@dataclass
class Simulation:
    command_contract_result: str = "fail"
    policy_evaluation_result: str = "UNKNOWN"
    capability_registry_result: str = "UNKNOWN"
    approval_required: bool = False
    approval_decision: str = "none"
    final_simulation_result: str = "SIMULATED_BLOCKED"
    simulated_action_class: str = "unknown"
    simulated_risk_level: str = "unknown"
    matched_capability_count: int = 0
    validation_error_count: int = 0
    sensitive_input_blocked: bool = False
    errors: list[str] = field(default_factory=list)
    command_fingerprint: str = "0" * 16
    policy_fingerprint: str = "0" * 16
    capability_fingerprint: str = "0" * 16
    created_at: str = ""
    simulation_id: str = ""


class LocalModuleLoadError(RuntimeError):
    """Raised when a local validation module cannot be imported."""


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    simulation = run_simulation(args)
    result = build_result(simulation)
    summary = render_summary(result)
    print(summary)

    if args.write_runtime_result or args.write_runtime_summary:
        if result["sensitiveInputBlocked"]:
            print("Runtime output blocked because sensitive input was detected.")
            return 1
        if args.write_runtime_result:
            write_runtime_json(result)
            print("Safe runtime simulation result written.")
        if args.write_runtime_summary:
            write_runtime_summary(summary)
            print("Safe runtime simulation summary written.")

    return exit_code(result)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the read-only agent simulator.")
    parser.add_argument("paths", nargs="*", help="Optional capability registry, policy, and command JSON files.")
    parser.add_argument("--approval-decision", choices=sorted(APPROVAL_DECISIONS))
    parser.add_argument("--write-runtime-result", action="store_true")
    parser.add_argument("--write-runtime-summary", action="store_true")
    args = parser.parse_args(argv)
    if len(args.paths) not in {0, 3}:
        parser.error("provide either no paths or exactly capability registry, policy, and command paths")
    return args


def run_simulation(args: argparse.Namespace) -> Simulation:
    simulation = Simulation(approval_decision=args.approval_decision or "none")
    simulation.created_at = utc_now()
    paths = args.paths if args.paths else [DEFAULT_CAPABILITY, DEFAULT_POLICY, DEFAULT_COMMAND]

    try:
        capability_path = safe_repo_path(paths[0], 1)
        policy_path = safe_repo_path(paths[1], 2)
        command_path = safe_repo_path(paths[2], 3)
        capability = load_json_file(capability_path, "capability registry")
        policy = load_json_file(policy_path, "policy")
        command = load_json_file(command_path, "command")
        simulation.capability_fingerprint = short_hash(capability)
        simulation.policy_fingerprint = short_hash(policy)
        simulation.command_fingerprint = short_hash(command)
        simulation.simulated_action_class = safe_action_class(command)
        simulation.simulated_risk_level = safe_risk_level(command)
        evaluate_command_contract(simulation, command)
        evaluate_policy(simulation, policy, command, command_path)
        evaluate_capability(simulation, capability_path, command_path)
    except ValueError as exc:
        simulation.errors.append(str(exc))
        simulation.validation_error_count += 1
        if "sensitive input" in str(exc):
            simulation.sensitive_input_blocked = True
    except (OSError, json.JSONDecodeError, LocalModuleLoadError):
        simulation.errors.append("input validation failed")
        simulation.validation_error_count += 1

    simulation.final_simulation_result = decide(simulation)
    simulation.simulation_id = "sim_" + short_hash(
        {
            "createdAt": simulation.created_at,
            "commandFingerprint": simulation.command_fingerprint,
            "policyFingerprint": simulation.policy_fingerprint,
            "capabilityFingerprint": simulation.capability_fingerprint,
            "finalSimulationResult": simulation.final_simulation_result,
        }
    )
    return simulation


def safe_repo_path(raw_path: str, input_index: int) -> Path:
    raw = Path(raw_path)
    candidate = (REPO_ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"input[{input_index}]: refused path outside repository") from exc
    return candidate


def load_json_file(path: Path, label: str) -> Any:
    if not path.is_file():
        raise ValueError(f"{label}: file does not exist")
    text = path.read_text(encoding="utf-8")
    if scan_string(text):
        raise ValueError(f"{label}: sensitive input blocked")
    payload = json.loads(text)
    if scan_value(payload):
        raise ValueError(f"{label}: sensitive input blocked")
    return payload


def scan_value(value: Any) -> bool:
    if isinstance(value, str):
        return scan_string(value)
    if isinstance(value, list):
        return any(scan_value(item) for item in value)
    if isinstance(value, dict):
        return any(scan_string(str(key)) or scan_value(item) for key, item in value.items())
    return False


def scan_string(value: str) -> bool:
    return any(pattern.search(value) for _, pattern in SENSITIVE_PATTERNS)


def load_module(module_name: str, relative_path: str) -> Any:
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise LocalModuleLoadError("local validation module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise LocalModuleLoadError("local validation module could not be loaded") from exc
    return module


def evaluate_command_contract(simulation: Simulation, command: Any) -> None:
    module = load_module("halo_sim_validate_agent_command", "scripts/validate-agent-command.py")
    validate_command = getattr(module, "validate_command", None)
    if not callable(validate_command) or not isinstance(command, dict):
        simulation.validation_error_count += 1
        return
    errors = validate_command(command, 1)
    simulation.command_contract_result = "pass" if not errors else "fail"
    simulation.validation_error_count += len(errors)
    if any("sensitive input" in error for error in errors):
        simulation.sensitive_input_blocked = True


def evaluate_policy(simulation: Simulation, policy: Any, command: Any, command_path: Path) -> None:
    module = load_module("halo_sim_evaluate_agent_policy", "scripts/evaluate-agent-policy.py")
    validate_command = getattr(module, "validate_command_with_contract", None)
    evaluate = getattr(module, "evaluate", None)
    if not callable(validate_command) or not callable(evaluate):
        simulation.validation_error_count += 1
        return
    command_valid, command_errors, command_failures = validate_command(command_path, command)
    evaluation = evaluate(policy, command, command_valid, command_errors)
    simulation.policy_evaluation_result = evaluation.decision if evaluation.decision in POLICY_RESULTS else "UNKNOWN"
    simulation.approval_required = simulation.approval_required or bool(evaluation.approval_required)
    simulation.validation_error_count += len(command_failures)
    if evaluation.validation_error_count > command_errors:
        simulation.validation_error_count += evaluation.validation_error_count - command_errors
    if evaluation.sensitive_input_blocked:
        simulation.sensitive_input_blocked = True


def evaluate_capability(simulation: Simulation, capability_path: Path, command_path: Path) -> None:
    module = load_module("halo_sim_validate_agent_capability", "scripts/validate-agent-capability.py")
    validate_registry = getattr(module, "validate_registry_and_command", None)
    if not callable(validate_registry):
        simulation.validation_error_count += 1
        return
    result = validate_registry(str(capability_path), str(command_path))
    simulation.capability_registry_result = result.status if result.status in CAPABILITY_RESULTS else "UNKNOWN"
    simulation.matched_capability_count = int(result.matching_capability_count)
    simulation.approval_required = simulation.approval_required or bool(result.approval_required_by_capability)
    simulation.validation_error_count += len(result.validation_errors)
    if result.sensitive_input_blocked:
        simulation.sensitive_input_blocked = True


def decide(simulation: Simulation) -> str:
    if simulation.command_contract_result != "pass":
        return "SIMULATED_BLOCKED"
    if simulation.policy_evaluation_result in {"DENY", "UNKNOWN"}:
        return "SIMULATED_BLOCKED"
    if simulation.capability_registry_result in {"FAIL", "UNKNOWN"}:
        return "SIMULATED_BLOCKED"
    if simulation.sensitive_input_blocked or simulation.validation_error_count > 0:
        return "SIMULATED_BLOCKED"
    if simulation.approval_required and simulation.approval_decision == "none":
        return "SIMULATED_REQUIRES_APPROVAL"
    if simulation.approval_required and simulation.approval_decision in {"denied", "expired"}:
        return "SIMULATED_BLOCKED"
    if simulation.approval_required and simulation.approval_decision == "approved":
        return "SIMULATED_READY"
    return "SIMULATED_READY"


def build_result(simulation: Simulation) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "resultType": "read_only_agent_simulation",
        "simulationId": simulation.simulation_id,
        "createdAt": simulation.created_at,
        "commandFingerprint": simulation.command_fingerprint,
        "policyFingerprint": simulation.policy_fingerprint,
        "capabilityFingerprint": simulation.capability_fingerprint,
        "commandContractResult": simulation.command_contract_result,
        "policyEvaluationResult": simulation.policy_evaluation_result,
        "capabilityRegistryResult": simulation.capability_registry_result,
        "approvalRequired": simulation.approval_required,
        "approvalDecision": simulation.approval_decision,
        "finalSimulationResult": simulation.final_simulation_result,
        "simulatedActionClass": simulation.simulated_action_class,
        "simulatedRiskLevel": simulation.simulated_risk_level,
        "matchedCapabilityCount": simulation.matched_capability_count,
        "validationErrorCount": simulation.validation_error_count,
        "sensitiveInputBlocked": simulation.sensitive_input_blocked,
        "executionAttempted": False,
        "networkContacted": False,
        "agentContacted": False,
        "filesystemMutationAttempted": False,
        "commandExecuted": False,
        "redaction": redaction_proof(),
    }


def redaction_proof() -> dict[str, bool]:
    return {
        "rawRequestIdsOmitted": True,
        "rawDeviceIdsOmitted": True,
        "rawServiceIdsOmitted": True,
        "rawPolicyIdsOmitted": True,
        "rawOperatorNamesOmitted": True,
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
        "rawCapabilityJsonOmitted": True,
        "rawAgentIdentifiersOmitted": True,
    }


def render_summary(result: dict[str, Any]) -> str:
    passed = result["finalSimulationResult"] in {"SIMULATED_READY", "SIMULATED_REQUIRES_APPROVAL"}
    lines = [
        f"# {BANNER}",
        "",
        f"Read-only Agent Simulator Result: {'PASS' if passed else 'FAIL'}",
        f"Final simulation result: {result['finalSimulationResult']}",
        f"Command contract result: {result['commandContractResult']}",
        f"Policy evaluation result: {result['policyEvaluationResult']}",
        f"Capability registry result: {result['capabilityRegistryResult']}",
        f"Approval required: {bool_word(result['approvalRequired'])}",
        f"Approval decision: {result['approvalDecision']}",
        f"Matched capability count: {result['matchedCapabilityCount']}",
        f"Execution attempted: no",
        f"Command executed: no",
        f"Network contacted: no",
        f"Agent contacted: no",
        f"Filesystem mutation attempted: no",
        f"Redacted fields stored: yes",
        f"Validation error count: {result['validationErrorCount']}",
        f"Sensitive input blocked: {bool_word(result['sensitiveInputBlocked'])}",
    ]
    return "\n".join(lines)


def write_runtime_json(result: dict[str, Any]) -> None:
    target = safe_runtime_target(RUNTIME_RESULT)
    text = json.dumps(result, indent=2, sort_keys=False) + "\n"
    assert_safe_output(text)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_runtime_summary(summary: str) -> None:
    target = safe_runtime_target(RUNTIME_SUMMARY)
    text = summary + "\n"
    assert_safe_output(text)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def safe_runtime_target(relative_target: Path) -> Path:
    target = (REPO_ROOT / relative_target).resolve()
    try:
        target.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError("runtime target outside repository") from exc
    if target.exists() and is_tracked(target):
        raise RuntimeError("refusing to overwrite tracked runtime output")
    return target


def assert_safe_output(text: str) -> None:
    if scan_string(text):
        raise RuntimeError("refusing to write unsafe simulation output")


def is_tracked(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError("refusing tracked check for path outside repository") from exc
    try:
        index_bytes = (REPO_ROOT / ".git" / "index").read_bytes()
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


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def short_hash(value: Any) -> str:
    if not isinstance(value, str):
        value = canonical_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_action_class(command: Any) -> str:
    if isinstance(command, dict) and command.get("mode") in ACTION_CLASSES:
        return str(command["mode"])
    return "unknown"


def safe_risk_level(command: Any) -> str:
    if isinstance(command, dict) and command.get("riskLevel") in RISK_LEVELS:
        return str(command["riskLevel"])
    return "unknown"


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def exit_code(result: dict[str, Any]) -> int:
    if result["finalSimulationResult"] in {"SIMULATED_READY", "SIMULATED_REQUIRES_APPROVAL"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
