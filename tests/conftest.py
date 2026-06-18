from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script_module(filename: str, module_name: str) -> Any:
    path = REPO_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_example(filename: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / "examples" / filename).read_text(encoding="utf-8"))


def health_command() -> dict[str, Any]:
    return load_example("agent-command.health-check.example.json")


def approval_command() -> dict[str, Any]:
    return load_example("agent-command.restart-service.requires-approval.example.json")


def policy() -> dict[str, Any]:
    return load_example("agent-policy.local.example.json")


def capability_registry() -> dict[str, Any]:
    return load_example("agent-capability.local.example.json")


def clone(value: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(value)
