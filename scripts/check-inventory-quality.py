#!/usr/bin/env python3
"""Run a safe local inventory quality gate without exposing raw inventory."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PATHS = [
    Path("inventory/devices.local.json"),
    Path("inventory/services.local.json"),
]

REPORT_PATH = Path("runtime/inventory-quality.local.md")
SAFE_BANNER = "SAFE QUALITY GATE ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"
SENSITIVE_FIELDS = {
    "ipHint",
    "hostHint",
    "localUrlHint",
    "accessMethod",
    "notes",
    "securityNotes",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a safe quality gate for ignored local inventory files."
    )
    parser.add_argument("paths", nargs="*", help="Optional local inventory JSON files.")
    parser.add_argument(
        "--write-runtime-report",
        action="store_true",
        help="Write the safe report to runtime/inventory-quality.local.md.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root()
    validator = load_validator(repo_root / "scripts" / "validate-inventory.py")
    paths = [Path(path) for path in args.paths] if args.paths else DEFAULT_PATHS
    existing_paths = [path for path in paths if path.is_file()]

    result = QualityResult()
    if args.paths:
        result.validation_errors += len(paths) - len(existing_paths)

    if not existing_paths and not args.paths:
        print("check-inventory-quality: no local inventory JSON files found; nothing to check")
        return 0

    devices: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []

    for path in existing_paths:
        if not is_repo_local_path(repo_root, path):
            result.blocked_sensitive_input = True
            result.validation_errors += 1
            continue

        text = read_text(path, result)
        if text is None:
            continue

        if validator.scan_text(path, text):
            result.blocked_sensitive_input = True
            result.validation_errors += 1
            break

        payload = parse_json(text, result)
        if payload is None:
            continue

        inventory_type = validator.infer_inventory_type(path, payload)
        if inventory_type is None:
            result.validation_errors += 1
            continue

        if not isinstance(payload, list):
            result.validation_errors += 1
            continue

        expected_fields = (
            validator.DEVICE_FIELDS
            if inventory_type == "device"
            else validator.SERVICE_FIELDS
        )
        allowed_types = (
            validator.DEVICE_TYPES
            if inventory_type == "device"
            else validator.SERVICE_TYPES
        )

        for index, entry in enumerate(payload):
            label = f"entry[{index}]"
            failures = validator.validate_entry(
                label, entry, expected_fields, allowed_types
            )
            result.validation_errors += len(failures)
            if not isinstance(entry, dict):
                continue

            result.empty_required_fields += count_empty_required_fields(
                entry, expected_fields
            )
            if inventory_type == "device":
                devices.append(entry)
            else:
                services.append(entry)

        if result.blocked_sensitive_input:
            break

    if not result.blocked_sensitive_input and not result.has_validation_blockers:
        run_quality_checks(devices, services, result)

    report = build_report(devices, services, result)
    print(report)

    if args.write_runtime_report:
        if is_tracked_path(REPORT_PATH):
            print("check-inventory-quality: refusing to overwrite a tracked runtime report")
            return 1
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report + "\n", encoding="utf-8")
        print("check-inventory-quality: wrote runtime/inventory-quality.local.md")

    return 1 if result.result_label == "FAIL" else 0


class QualityResult:
    def __init__(self) -> None:
        self.blocked_sensitive_input = False
        self.invalid_json = 0
        self.validation_errors = 0
        self.validation_warnings = 0
        self.empty_required_fields = 0
        self.duplicate_device_ids = 0
        self.duplicate_service_ids = 0
        self.missing_owner_references = 0
        self.unknown_device_statuses = 0
        self.unknown_service_statuses = 0
        self.missing_device_runbooks = 0
        self.missing_service_runbooks = 0
        self.service_runbook_supported = False

    @property
    def has_validation_blockers(self) -> bool:
        return (
            self.blocked_sensitive_input
            or self.invalid_json > 0
            or self.validation_errors > 0
            or self.empty_required_fields > 0
        )

    @property
    def error_count(self) -> int:
        return (
            self.invalid_json
            + self.validation_errors
            + self.empty_required_fields
            + self.duplicate_device_ids
            + self.duplicate_service_ids
            + self.missing_owner_references
        )

    @property
    def warning_count(self) -> int:
        return (
            self.validation_warnings
            + self.unknown_device_statuses
            + self.unknown_service_statuses
            + self.missing_device_runbooks
            + self.missing_service_runbooks
        )

    @property
    def result_label(self) -> str:
        if self.blocked_sensitive_input or self.error_count > 0:
            return "FAIL"
        if self.warning_count > 0:
            return "WARN"
        return "PASS"


def find_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_validator(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("halo_validate_inventory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load inventory validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_repo_local_path(repo_root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(repo_root)
    except ValueError:
        return False
    return True


def read_text(path: Path, result: QualityResult) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        result.validation_errors += 1
        return None


def parse_json(text: str, result: QualityResult) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        result.invalid_json += 1
        return None


def count_empty_required_fields(
    entry: dict[str, Any], expected_fields: list[str]
) -> int:
    empty_count = 0
    for field in expected_fields:
        value = entry.get(field)
        if isinstance(value, str) and not value.strip():
            empty_count += 1
    return empty_count


def run_quality_checks(
    devices: list[dict[str, Any]],
    services: list[dict[str, Any]],
    result: QualityResult,
) -> None:
    result.duplicate_device_ids = count_duplicate_ids(devices)
    result.duplicate_service_ids = count_duplicate_ids(services)
    result.unknown_device_statuses = count_status(devices, "unknown")
    result.unknown_service_statuses = count_status(services, "unknown")
    result.missing_device_runbooks = count_blank_field(devices, "runbook")
    result.service_runbook_supported = any("runbook" in service for service in services)
    if result.service_runbook_supported:
        result.missing_service_runbooks = count_blank_field(services, "runbook")

    device_ids = {
        value.strip()
        for value in (device.get("id") for device in devices)
        if isinstance(value, str) and value.strip()
    }
    for service in services:
        owner = service.get("ownerDeviceId")
        if isinstance(owner, str) and owner.strip() and owner.strip() not in device_ids:
            result.missing_owner_references += 1


def count_duplicate_ids(entries: list[dict[str, Any]]) -> int:
    ids = Counter(
        value.strip()
        for value in (entry.get("id") for entry in entries)
        if isinstance(value, str) and value.strip()
    )
    return sum(count - 1 for count in ids.values() if count > 1)


def count_status(entries: list[dict[str, Any]], status: str) -> int:
    return sum(1 for entry in entries if entry.get("status") == status)


def count_blank_field(entries: list[dict[str, Any]], field: str) -> int:
    count = 0
    for entry in entries:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            count += 1
    return count


def is_tracked_path(path: Path) -> bool:
    git_dir = Path(".git")
    if not git_dir.exists():
        return False
    import subprocess

    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def build_report(
    devices: list[dict[str, Any]],
    services: list[dict[str, Any]],
    result: QualityResult,
) -> str:
    service_runbook_note = (
        "checked"
        if result.service_runbook_supported
        else "not checked; service schema does not support runbook yet"
    )
    lines = [
        "# Local Inventory Quality Gate",
        "",
        SAFE_BANNER,
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Quality Gate Result: {result.result_label}",
        "",
        "## Totals",
        "",
        f"- Total devices: {len(devices)}",
        f"- Total services: {len(services)}",
        f"- Error count: {result.error_count}",
        f"- Warning count: {result.warning_count}",
        "",
        "## Checks",
        "",
        f"- Duplicate device ID count: {result.duplicate_device_ids}",
        f"- Duplicate service ID count: {result.duplicate_service_ids}",
        f"- Missing owner reference count: {result.missing_owner_references}",
        f"- Unknown device status count: {result.unknown_device_statuses}",
        f"- Unknown service status count: {result.unknown_service_statuses}",
        f"- Missing device runbook count: {result.missing_device_runbooks}",
        f"- Missing service runbook count: {result.missing_service_runbooks}",
        f"- Validation warning count: {result.validation_warnings}",
        f"- Empty required field count: {result.empty_required_fields}",
        f"- Invalid JSON count: {result.invalid_json}",
        f"- Service runbook check: {service_runbook_note}",
        "",
        "## Safety",
        "",
        f"- Blocked sensitive input: {format_bool(result.blocked_sensitive_input)}",
        "- Network scans: not performed",
        "- Reachability checks: not performed",
        "- Remote commands: not performed",
        "- Secret reads: not performed",
    ]
    return "\n".join(lines)


def format_bool(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    sys.exit(main())
