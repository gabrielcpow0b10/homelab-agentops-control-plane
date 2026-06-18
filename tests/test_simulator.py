from __future__ import annotations

import argparse

from conftest import load_script_module


def _args(paths: list[str] | None = None, approval_decision: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        paths=paths or [],
        approval_decision=approval_decision,
        write_runtime_result=False,
        write_runtime_summary=False,
    )


def test_default_read_only_example_results_in_simulated_ready() -> None:
    simulator = load_script_module("simulate-readonly-agent.py", "test_simulator_default")

    result = simulator.run_simulation(_args())

    assert result.final_simulation_result == "SIMULATED_READY"
    assert result.command_contract_result == "pass"
    assert result.policy_evaluation_result == "ALLOW"
    assert result.capability_registry_result == "PASS"


def test_approval_required_command_without_approval_requires_approval() -> None:
    simulator = load_script_module("simulate-readonly-agent.py", "test_simulator_no_approval")
    paths = [
        "examples/agent-capability.local.example.json",
        "examples/agent-policy.local.example.json",
        "examples/agent-command.restart-service.requires-approval.example.json",
    ]

    result = simulator.run_simulation(_args(paths=paths))

    assert result.final_simulation_result == "SIMULATED_REQUIRES_APPROVAL"
    assert result.approval_required is True
    assert result.policy_evaluation_result == "ALLOW_WITH_APPROVAL"
    assert result.capability_registry_result == "WARN"


def test_approval_required_command_with_approved_decision_is_ready() -> None:
    simulator = load_script_module("simulate-readonly-agent.py", "test_simulator_approved")
    paths = [
        "examples/agent-capability.local.example.json",
        "examples/agent-policy.local.example.json",
        "examples/agent-command.restart-service.requires-approval.example.json",
    ]

    result = simulator.run_simulation(_args(paths=paths, approval_decision="approved"))

    assert result.final_simulation_result == "SIMULATED_READY"


def test_approval_required_command_with_denied_or_expired_decision_is_blocked() -> None:
    simulator = load_script_module("simulate-readonly-agent.py", "test_simulator_denied")
    paths = [
        "examples/agent-capability.local.example.json",
        "examples/agent-policy.local.example.json",
        "examples/agent-command.restart-service.requires-approval.example.json",
    ]

    denied = simulator.run_simulation(_args(paths=paths, approval_decision="denied"))
    expired = simulator.run_simulation(_args(paths=paths, approval_decision="expired"))

    assert denied.final_simulation_result == "SIMULATED_BLOCKED"
    assert expired.final_simulation_result == "SIMULATED_BLOCKED"


def test_unsafe_command_contract_failure_remains_blocked() -> None:
    simulator = load_script_module("simulate-readonly-agent.py", "test_simulator_decide")
    simulation = simulator.Simulation(
        command_contract_result="fail",
        policy_evaluation_result="ALLOW",
        capability_registry_result="PASS",
    )

    assert simulator.decide(simulation) == "SIMULATED_BLOCKED"
