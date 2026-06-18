from __future__ import annotations

import json
from pathlib import Path

from conftest import capability_registry, clone, health_command, approval_command, load_script_module


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path.name


def _prepare_module(tmp_path, monkeypatch):
    capability = load_script_module("validate-agent-capability.py", "test_capability_module")
    monkeypatch.setattr(capability, "REPO_ROOT", tmp_path.resolve())
    monkeypatch.setattr(capability, "validate_command_with_contract", lambda _path, _command: [])
    return capability


def test_command_with_no_matching_capability_fails(tmp_path, monkeypatch) -> None:
    capability = _prepare_module(tmp_path, monkeypatch)
    registry = clone(capability_registry())
    command = clone(health_command())
    command["action"] = "temperature_check"

    registry_path = _write_json(tmp_path / "registry.json", registry)
    command_path = _write_json(tmp_path / "command.json", command)
    result = capability.validate_registry_and_command(registry_path, command_path)

    assert result.status == "FAIL"
    assert result.matching_capability_count == 0
    assert any("no enabled matching capability" in error for error in result.validation_errors)


def test_matching_public_capability_passes_safely(tmp_path, monkeypatch) -> None:
    capability = _prepare_module(tmp_path, monkeypatch)

    registry_path = _write_json(tmp_path / "registry.json", capability_registry())
    command_path = _write_json(tmp_path / "command.json", health_command())
    result = capability.validate_registry_and_command(registry_path, command_path)

    assert result.status == "PASS"
    assert result.matching_capability_count >= 1
    assert result.sensitive_input_blocked is False


def test_matching_approval_required_capability_warns_safely(tmp_path, monkeypatch) -> None:
    capability = _prepare_module(tmp_path, monkeypatch)

    registry_path = _write_json(tmp_path / "registry.json", capability_registry())
    command_path = _write_json(tmp_path / "command.json", approval_command())
    result = capability.validate_registry_and_command(registry_path, command_path)

    assert result.status == "WARN"
    assert result.matching_capability_count == 1
    assert result.approval_required_by_capability is True
    assert result.validation_errors == []


def test_capability_validation_reports_no_agent_or_network_contact(tmp_path, monkeypatch) -> None:
    capability = _prepare_module(tmp_path, monkeypatch)

    registry_path = _write_json(tmp_path / "registry.json", capability_registry())
    command_path = _write_json(tmp_path / "command.json", health_command())
    result = capability.validate_registry_and_command(registry_path, command_path)
    summary = capability.render_summary(result)

    assert "Execution attempted: no" in summary
    assert "Network contacted: no" in summary
    assert "Agent contacted: no" in summary
