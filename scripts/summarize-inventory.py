#!/usr/bin/env python3
"""Generate a redacted local inventory summary without exposing raw inventory."""

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

REPORT_PATH = Path("runtime/inventory-summary.local.md")
SAFE_BANNER = "SAFE SUMMARY ONLY - NO RAW HOSTS, IPS, URLS, TOKENS, OR SECRETS"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a safe, redacted summary of local inventory JSON files."
    )
    parser.add_argument("paths", nargs="*", help="Optional local inventory JSON files.")
    parser.add_argument(
        "--write-runtime-report",
        action="store_true",
        help="Write the safe summary to runtime/inventory-summary.local.md.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root()
    validator = load_validator(repo_root / "scripts" / "validate-inventory.py")
    paths = [Path(path) for path in args.paths] if args.paths else DEFAULT_PATHS
    existing_paths = [path for path in paths if path.is_file()]

    if not existing_paths:
        print("summarize-inventory: no local inventory JSON files found; nothing to summarize")
        return 0

    blocked: list[str] = []
    warnings: list[str] = []
    devices: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []

    for path in existing_paths:
        path_errors = ensure_repo_local_path(repo_root, path)
        if path_errors:
            blocked.extend(path_errors)
            continue

        text = read_inventory_text(repo_root, path, blocked)
        if text is None:
            continue

        scan_failures = validator.scan_text(path, text)
        if scan_failures:
            blocked.append(f"{safe_path_label(repo_root, path)}: blocked sensitive or private pattern found")
            continue

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            warnings.append(
                f"{safe_path_label(repo_root, path)}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            )
            continue

        inventory_type = validator.infer_inventory_type(path, payload)
        if inventory_type is None:
            warnings.append(
                f"{safe_path_label(repo_root, path)}: could not infer inventory type; use a devices, inventory, or services filename"
            )
            continue

        if not isinstance(payload, list):
            warnings.append(f"{safe_path_label(repo_root, path)}: top-level JSON value must be an array")
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
            label = f"{safe_path_label(repo_root, path)}[{index}]"
            entry_warnings = validator.validate_entry(
                label, entry, expected_fields, allowed_types
            )
            warnings.extend(entry_warnings)
            if not isinstance(entry, dict):
                continue
            if inventory_type == "device":
                devices.append(entry)
            else:
                services.append(entry)

    if blocked:
        print("summarize-inventory: failed; blocked sensitive or unsafe input")
        for failure in blocked:
            print(f"  - {failure}")
        return 1

    report = build_report(devices, services, len(warnings))
    print(report)

    if args.write_runtime_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report + "\n", encoding="utf-8")
        print(f"summarize-inventory: wrote {REPORT_PATH}")

    if warnings:
        print(f"summarize-inventory: validation warning count: {len(warnings)}")

    return 0


def find_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_validator(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("halo_validate_inventory", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_repo_local_path(repo_root: Path, path: Path) -> list[str]:
    try:
        resolved = path.resolve()
        resolved.relative_to(repo_root)
    except ValueError:
        return ["<outside-repository-path>: refusing to read a path outside the repository"]
    return []


def read_inventory_text(repo_root: Path, path: Path, blocked: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        blocked.append(f"{safe_path_label(repo_root, path)}: could not read file: {exc}")
        return None


def safe_path_label(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return "<outside-repository-path>"


def build_report(
    devices: list[dict[str, Any]],
    services: list[dict[str, Any]],
    warning_count: int,
) -> str:
    device_status = count_field(devices, "status")
    device_type = count_field(devices, "type")
    service_status = count_field(services, "status")
    service_type = count_field(services, "type")
    owner_counts = count_owner_device_links(services)

    lines = [
        "# Local Inventory Summary",
        "",
        SAFE_BANNER,
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Totals",
        "",
        f"- Total devices: {len(devices)}",
        f"- Total services: {len(services)}",
        f"- Devices missing runbook: {count_blank_field(devices, 'runbook')}",
        f"- Devices with status unknown: {device_status.get('unknown', 0)}",
        f"- Services with status unknown: {service_status.get('unknown', 0)}",
        f"- Validation warning count: {warning_count}",
        "",
        "## Devices By Status",
        "",
        *format_counter(device_status),
        "",
        "## Devices By Type",
        "",
        *format_counter(device_type),
        "",
        "## Services By Status",
        "",
        *format_counter(service_status),
        "",
        "## Services By Type",
        "",
        *format_counter(service_type),
        "",
        "## Services By Owner Device Reference",
        "",
        f"- Services with ownerDeviceId: {owner_counts['linked_services']}",
        f"- Services missing ownerDeviceId: {owner_counts['missing_owner']}",
        f"- Unique ownerDeviceId references: {owner_counts['unique_owners']}",
        *format_owner_distribution(owner_counts["services_per_owner"]),
    ]
    return "\n".join(lines)


def count_field(entries: list[dict[str, Any]], field: str) -> Counter[str]:
    values: Counter[str] = Counter()
    for entry in entries:
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            values[value] += 1
        else:
            values["missing"] += 1
    return values


def count_blank_field(entries: list[dict[str, Any]], field: str) -> int:
    count = 0
    for entry in entries:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            count += 1
    return count


def count_owner_device_links(services: list[dict[str, Any]]) -> dict[str, Any]:
    owner_ids: Counter[str] = Counter()
    missing_owner = 0
    for service in services:
        value = service.get("ownerDeviceId")
        if isinstance(value, str) and value.strip():
            owner_ids[value] += 1
        else:
            missing_owner += 1

    services_per_owner = Counter(owner_ids.values())
    return {
        "linked_services": sum(owner_ids.values()),
        "missing_owner": missing_owner,
        "unique_owners": len(owner_ids),
        "services_per_owner": services_per_owner,
    }


def format_counter(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["- none: 0"]
    return [f"- {key}: {counter[key]}" for key in sorted(counter)]


def format_owner_distribution(counter: Counter[int]) -> list[str]:
    if not counter:
        return ["- Owner references with any service count: 0"]
    return [
        f"- Owner references with {service_count} service(s): {owner_count}"
        for service_count, owner_count in sorted(counter.items())
    ]


if __name__ == "__main__":
    sys.exit(main())
