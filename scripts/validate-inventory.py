#!/usr/bin/env python3
"""Validate ignored local inventory JSON files without external dependencies."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEVICE_FIELDS = [
    "id",
    "name",
    "type",
    "role",
    "status",
    "location",
    "hostHint",
    "ipHint",
    "accessMethod",
    "notes",
    "securityNotes",
    "runbook",
    "createdAt",
    "updatedAt",
]

SERVICE_FIELDS = [
    "id",
    "name",
    "type",
    "status",
    "ownerDeviceId",
    "localUrlHint",
    "portHint",
    "notes",
    "securityNotes",
    "createdAt",
    "updatedAt",
]

DEVICE_TYPES = {
    "ai_node",
    "server",
    "raspberry_pi",
    "nas",
    "router",
    "storage",
    "service",
    "workstation",
    "other",
}

SERVICE_TYPES = {
    "ai_runtime",
    "dashboard",
    "backup",
    "storage",
    "monitoring",
    "database",
    "web_app",
    "network",
    "automation",
    "other",
}

STATUSES = {"online", "offline", "unknown", "planned", "maintenance"}

SECRET_PATTERNS = [
    "password" + "=",
    "token" + "=",
    "api_key" + "=",
    "apikey" + "=",
    "secret" + "=",
    "ghp" + "_",
    "github_pat" + "_",
    "ak" + "ia",
    "begin openssh private " + "key",
    "begin rsa private " + "key",
    "." + "env",
    "." + "ssh",
]

PRIVATE_PATH_PATTERNS = ["/" + "Users/", "~" + "/HomeLab"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate HomeLab local inventory JSON files."
    )
    parser.add_argument("paths", nargs="*", help="Optional JSON files to validate.")
    args = parser.parse_args()

    paths = [Path(path) for path in args.paths] if args.paths else discover_inventory()
    if not paths:
        print("validate-inventory: no local inventory JSON files found; nothing to validate")
        return 0

    failures: list[str] = []
    for path in paths:
        failures.extend(validate_path(path))

    if failures:
        print("validate-inventory: failed")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"validate-inventory: passed ({len(paths)} file(s))")
    return 0


def discover_inventory() -> list[Path]:
    inventory_dir = Path("inventory")
    if not inventory_dir.is_dir():
        return []
    return [Path(path) for path in sorted(glob.glob("inventory/*.json"))]


def validate_path(path: Path) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        return [f"{path}: file does not exist"]

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: could not read file: {exc}"]

    failures.extend(scan_text(path, text))

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        failures.append(f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return failures

    inventory_type = infer_inventory_type(path, payload)
    if inventory_type is None:
        failures.append(f"{path}: could not infer inventory type; use a devices, inventory, or services filename")
        return failures

    if not isinstance(payload, list):
        failures.append(f"{path}: top-level JSON value must be an array")
        return failures

    for index, entry in enumerate(payload):
        label = f"{path}[{index}]"
        if inventory_type == "device":
            failures.extend(validate_entry(label, entry, DEVICE_FIELDS, DEVICE_TYPES))
        else:
            failures.extend(validate_entry(label, entry, SERVICE_FIELDS, SERVICE_TYPES))

    return failures


def infer_inventory_type(path: Path, payload: Any) -> str | None:
    name = path.name.lower()
    if "service" in name:
        return "service"
    if "device" in name or "inventory" in name:
        return "device"
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            if "runbook" in first or "accessMethod" in first:
                return "device"
            if "ownerDeviceId" in first or "localUrlHint" in first:
                return "service"
    return None


def validate_entry(
    label: str,
    entry: Any,
    expected_fields: list[str],
    allowed_types: set[str],
) -> list[str]:
    failures: list[str] = []
    if not isinstance(entry, dict):
        return [f"{label}: entry must be an object"]

    missing = [field for field in expected_fields if field not in entry]
    extra = [field for field in entry if field not in expected_fields]
    if missing:
        failures.append(f"{label}: missing required field(s): {', '.join(missing)}")
    if extra:
        failures.append(f"{label}: unexpected field(s): {', '.join(extra)}")

    for field in expected_fields:
        if field not in entry:
            continue
        value = entry[field]
        if not isinstance(value, str):
            failures.append(f"{label}.{field}: value must be a string")
        elif field in {"id", "name"} and not value.strip():
            failures.append(f"{label}.{field}: value must not be empty")

    entry_type = entry.get("type")
    if isinstance(entry_type, str) and entry_type not in allowed_types:
        failures.append(f"{label}.type: unsupported value {entry_type!r}")

    status = entry.get("status")
    if isinstance(status, str) and status not in STATUSES:
        failures.append(f"{label}.status: unsupported value {status!r}")

    for field in ("createdAt", "updatedAt"):
        value = entry.get(field)
        if isinstance(value, str) and not is_iso_datetime(value):
            failures.append(f"{label}.{field}: value must be an ISO-8601 date-time")

    return failures


def is_iso_datetime(value: str) -> bool:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def scan_text(path: Path, text: str) -> list[str]:
    failures: list[str] = []
    lowered = text.lower()
    for pattern in SECRET_PATTERNS:
        if pattern in lowered:
            failures.append(f"{path}: blocked secret-like pattern found: {pattern}")
    for pattern in PRIVATE_PATH_PATTERNS:
        if pattern in text:
            failures.append(f"{path}: blocked private path pattern found: {pattern}")
    return failures


if __name__ == "__main__":
    sys.exit(main())
