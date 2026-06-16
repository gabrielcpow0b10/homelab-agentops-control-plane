# v0.2-local Local Inventory Runtime

## Purpose

v0.2-local adds a local inventory runtime for HomeLab Control Plane. It provides ignored local JSON files for device and service records, tracked sanitized templates, and validation scripts that can be run before local review or future integration work.

This version keeps the repository as a private-oriented control-plane foundation. It does not add network scanning, remote execution, cloud provider support, camera support, external services, or application UI code.

## Why Local Inventory Is Ignored

Real inventory can expose operational details. Device names, service endpoints, local addresses, notes, access methods, and runbook references may reveal sensitive topology even when they do not contain credentials.

For that reason, `inventory/` and related runtime directories are ignored by Git. Tracked files should stay limited to fake examples, schemas, scripts, and documentation.

## Initialize Local Inventory

Run:

```bash
bash scripts/init-local-inventory.sh
```

The initializer creates `inventory/` and copies sanitized templates only when the destination files do not already exist:

- `inventory/devices.local.json`
- `inventory/services.local.json`

The script never overwrites existing local inventory.

## Validate Local Inventory

Run:

```bash
python3 scripts/validate-inventory.py
```

With no arguments, the validator checks existing JSON files under `inventory/`. If the directory does not exist or no JSON files are present, it exits successfully with a clear message.

Specific files can also be validated:

```bash
python3 scripts/validate-inventory.py inventory/devices.local.json inventory/services.local.json
```

The repository doctor also runs the validator:

```bash
bash scripts/doctor.sh
```

## What Can Be Stored Locally

Ignored local inventory may contain sanitized operational records needed for personal use, such as:

- Device records.
- Service records.
- Generic local access hints.
- Maintenance status.
- Runbook identifiers.
- Non-secret notes.
- Security review notes.

Keep the data minimal and avoid turning local inventory into a credential store.

## What Must Never Be Stored

Do not store:

- Passwords, tokens, API keys, SSH keys, private keys, or credentials.
- `.env` content.
- Real device secrets.
- Private logs.
- Screenshots.
- Uploaded documents.
- PDFs.
- Recovery keys.
- Shell commands that execute against remote machines.
- Network scanning targets or results.

Tracked repository files must also avoid real IP addresses, real hostnames, private filesystem paths, and personal machine names.

## Future HALO Console Integration

A later HALO Console integration may read the local inventory files as a local-only source of device and service metadata. That integration should be read-only by default, should preserve the ignored-file boundary, and should not introduce cloud synchronization or remote execution.

The control plane remains the source for durable schemas, examples, validation, and safety rules. HALO Console can become an application layer on top of that local data.

## Limitations

- Validation uses Python standard library checks only.
- Validation does not prove that an endpoint is reachable.
- Validation does not scan networks.
- Validation does not execute shell commands against devices.
- Validation cannot determine whether every free-text note is safe; review remains required.
- Local inventory is intentionally ignored by Git and is not backed up by this repository.

## v0.3 Next-Step Plan

- Add stricter schema alignment for local inventory files.
- Add optional runbook validation for local-only records.
- Add read-only export formats for future console consumption.
- Add clearer separation between sanitized examples and ignored operational records.
- Keep the default workflow local, private-oriented, and dependency-free.
