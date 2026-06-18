from __future__ import annotations

from conftest import clone, health_command, approval_command, load_script_module


def test_blocked_shell_command_returns_validation_errors() -> None:
    validator = load_script_module("validate-agent-command.py", "test_validate_agent_command_blocked")
    command = clone(health_command())
    command["action"] = "shell_command"

    errors = validator.validate_command(command, 1)

    assert errors
    assert any("blocked action requested" in error for error in errors)


def test_unknown_action_returns_validation_errors() -> None:
    validator = load_script_module("validate-agent-command.py", "test_validate_agent_command_unknown")
    command = clone(health_command())
    command["action"] = "invented_action"

    errors = validator.validate_command(command, 1)

    assert errors
    assert any("unknown action requested" in error for error in errors)


def test_approved_write_without_required_rules_is_rejected() -> None:
    validator = load_script_module("validate-agent-command.py", "test_validate_agent_command_bad_write")
    command = clone(approval_command())
    command["mode"] = "read_only"
    command["riskLevel"] = "medium"
    command["requiresApproval"] = False
    command["dryRun"] = True

    errors = validator.validate_command(command, 1)

    assert any("approved-write action has invalid mode" in error for error in errors)
    assert any("approved-write action must be dryRun false" in error for error in errors)
    assert any("approved-write action must require approval" in error for error in errors)
    assert any("approved-write action must be high risk" in error for error in errors)


def test_sanitized_read_only_health_check_example_validates_successfully() -> None:
    validator = load_script_module("validate-agent-command.py", "test_validate_agent_command_health")

    errors = validator.validate_command(health_command(), 1)

    assert errors == []
