# v0.3-local Safe Inventory Summary

## Purpose

v0.3-local adds a safe local report layer for ignored inventory JSON files. The report is intended for quick review of local control-plane shape and readiness without exposing operational details.

The summary is count-based and redacted by design. It does not list raw hosts, addresses, URLs, access methods, notes, security notes, tokens, or secrets.

## Why The Report Is Local-Only

Local inventory can contain sensitive topology and operational context. Even when it does not contain credentials, raw device hints, service hints, names, and notes can reveal private details.

For that reason, generated reports are written only under `runtime/`, which is ignored by Git. The report can be recreated from ignored local inventory files and should not be committed.

## What The Report Includes

The safe summary includes:

- Total devices.
- Total services.
- Devices by status.
- Devices by type.
- Services by status.
- Services by type.
- Owner device reference counts without listing owner IDs.
- Count of devices missing runbook.
- Count of devices with status `unknown`.
- Count of services with status `unknown`.
- Validation warning count.

## What The Report Never Includes

The report must never include:

- Raw host hints.
- Raw address hints.
- Raw local URL hints.
- Access methods.
- Notes or security notes.
- Private filesystem paths.
- Passwords, tokens, API keys, SSH keys, private keys, or `.env` content.
- Screenshots, uploaded documents, PDFs, private logs, or raw inventory details.

If suspicious secret-like or private-path patterns are found in the input, summary generation fails and no report is written.

## Run The Summary

Print a safe summary to stdout:

```bash
python3 scripts/summarize-inventory.py
```

Summarize explicit inventory files:

```bash
python3 scripts/summarize-inventory.py inventory/devices.local.json inventory/services.local.json
```

Write the ignored runtime report:

```bash
bash scripts/report-inventory.sh
```

The helper validates local inventory first, writes `runtime/inventory-summary.local.md`, and confirms the runtime directory is ignored by Git.

## Future HALO Console Connection

A later HALO Console integration can safely consume this layer by reading only the generated count-based report or by using the same redaction rules before displaying inventory health. The console should treat raw local inventory as a private source, keep access read-only by default, and avoid exposing raw hints in UI views intended for sharing or export.

## Limitations

- The report is a summary, not a complete inventory export.
- The script does not check whether devices or services are reachable.
- The script does not scan networks.
- The script does not execute shell commands against remote machines.
- The validation warning count is a local review signal and does not replace manual review.
- Ignored runtime reports are not backed up by this repository.

## v0.4 Next-Step Ideas

- Add runbook coverage summaries.
- Add stale-record age buckets without listing record names.
- Add schema-version reporting.
- Add local-only machine-readable summary output for read-only console use.
- Add stricter redaction tests for future report formats.
