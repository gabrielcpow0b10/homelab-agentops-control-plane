from __future__ import annotations

from conftest import clone, health_command, approval_command, load_script_module, policy


def test_unknown_action_remains_deny() -> None:
    engine = load_script_module("evaluate-agent-policy.py", "test_policy_unknown")
    command = clone(health_command())
    command["action"] = "invented_action"

    result = engine.evaluate(policy(), command, command_valid=True, validation_errors=0)

    assert result.decision == engine.DECISION_DENY
    assert result.allowed_action_match_count == 0


def test_allowed_action_for_non_matching_device_remains_deny() -> None:
    engine = load_script_module("evaluate-agent-policy.py", "test_policy_device")
    command = clone(health_command())
    command["targetDeviceId"] = "device_beta"

    result = engine.evaluate(policy(), command, command_valid=True, validation_errors=0)

    assert result.decision == engine.DECISION_DENY
    assert result.matching_device_count == 0


def test_denied_action_explicitly_listed_in_policy_remains_deny() -> None:
    engine = load_script_module("evaluate-agent-policy.py", "test_policy_denied")
    command = clone(health_command())
    command["action"] = "shell_command"

    result = engine.evaluate(policy(), command, command_valid=True, validation_errors=0)

    assert result.decision == engine.DECISION_DENY
    assert result.denied_action_match_count == 1


def test_read_only_health_check_allows_when_policy_conditions_match() -> None:
    engine = load_script_module("evaluate-agent-policy.py", "test_policy_allow")
    command = health_command()
    command_valid, validation_errors, validation_failures = engine.validate_command_with_contract(command)

    result = engine.evaluate(policy(), command, command_valid, validation_errors)
    result.validation_failures.extend(validation_failures)

    assert result.decision == engine.DECISION_ALLOW
    assert result.approval_required is False
    assert result.contract_valid is True
    assert result.validation_error_count == 0


def test_invalid_command_fails_contract_and_policy_safely() -> None:
    engine = load_script_module("evaluate-agent-policy.py", "test_policy_invalid_contract")
    command = clone(health_command())
    command["mode"] = "approved_write"
    command_valid, validation_errors, validation_failures = engine.validate_command_with_contract(command)

    result = engine.evaluate(policy(), command, command_valid, validation_errors)
    result.validation_failures.extend(validation_failures)

    assert result.decision == engine.DECISION_DENY
    assert result.contract_valid is False
    assert result.validation_error_count > 0


def test_approval_required_action_returns_allow_with_approval() -> None:
    engine = load_script_module("evaluate-agent-policy.py", "test_policy_approval")

    result = engine.evaluate(policy(), approval_command(), command_valid=True, validation_errors=0)

    assert result.decision == engine.DECISION_APPROVAL
    assert result.approval_required is True
