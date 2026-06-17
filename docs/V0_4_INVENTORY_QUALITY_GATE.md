# v0.4-local Inventory Quality Gate

## Purpose

The v0.4-local inventory quality gate checks ignored local inventory files for structural quality issues after validation. It produces a redacted Markdown report with PASS, WARN, or FAIL so local inventory can be reviewed without exposing operational details.

## Local-Only Behavior

The gate reads the ignored default files:

- `inventory/devices.local.json`
- `inventory/services.local.json`

It can also read explicit local paths:

```bash
python3 scripts/check-inventory-quality.py inventory/devices.local.json inventory/services.local.json
```

The gate does not scan the network, check reachability, execute remote commands, or read secrets. Runtime reports are written only when requested and go to the ignored path `runtime/inventory-quality.local.md`.

## PASS, WARN, FAIL

- `PASS`: validation succeeded and no quality warnings were found.
- `WARN`: validation succeeded, but unknown statuses or missing runbooks need review.
- `FAIL`: blocked sensitive input, invalid JSON, validation errors, duplicate IDs, or missing owner references were found.

## What Is Checked

- Duplicate device IDs.
- Duplicate service IDs.
- Services referencing missing `ownerDeviceId` values.
- Devices with `status` set to `unknown`.
- Services with `status` set to `unknown`.
- Devices missing `runbook`.
- Empty required fields after validation.
- Validation blockers such as unsupported type or status values.

Service runbooks are not checked yet because the current service schema does not include a `runbook` field.

## What Is Never Exposed

The quality report never prints raw host hints, IP hints, URL hints, access methods, notes, security notes, tokens, secrets, or private filesystem paths. If secret-like or private-path patterns are found in an input file, the gate fails immediately with a redacted failure report.

## Commands

Run the no-write quality gate:

```bash
python3 scripts/check-inventory-quality.py
```

Run the quality gate with explicit local files:

```bash
python3 scripts/check-inventory-quality.py inventory/devices.local.json inventory/services.local.json
```

Validate inventory and write the ignored runtime report:

```bash
bash scripts/check-inventory-quality.sh
```

Run the full local doctor:

```bash
bash scripts/doctor.sh
```

Doctor compiles and runs the quality gate without writing runtime reports.

## Future AI-to-Agent Control

The gate prepares the repository for future AI-to-agent control by separating inventory quality from sensitive operational details. A local agent can receive redacted PASS, WARN, or FAIL signals before any future command flow is considered, while raw hosts, URLs, notes, and access methods remain outside generated reports.

## Limitations

- This is a local static quality gate only.
- It does not prove that a device or service is reachable.
- It does not inspect runtime state.
- It does not resolve service ownership beyond local `ownerDeviceId` references.
- It does not check service runbooks until the service schema supports a `runbook` field.

## v0.5 Next-Step Idea

The next local milestone can define an Agent Command Contract: a small, explicit schema for permitted local agent requests, required preflight gates, redacted inputs, dry-run behavior, and command result reporting.
