# v0.5-local Agent Command Contract

## Purpose

v0.5-local defines the first safe JSON command contract for future HomeLab agents. It lets HALO or another local AI propose a structured request while the Control Plane validates that request before any future execution layer can act on it.

This milestone validates contracts only. It does not contact an agent, run an action, execute a shell command, scan a network, or perform local maintenance.

## Safety Model

- AI proposes a JSON command request.
- Control Plane validates schema, field types, allowed actions, approval rules, parameters, and sensitive-pattern blocking.
- Future agents may execute only allowlisted actions after validation.
- Arbitrary shell execution is never part of the contract.
- Dangerous or write actions require explicit approval.
- Normal reports are redacted and count based.

## Allowed Actions

- `health_check`
- `disk_status`
- `memory_status`
- `temperature_check`
- `service_status`
- `backup_dry_run`
- `backup_run`
- `security_scan`
- `log_summary`
- `restart_allowed_service`

## Blocked Actions

- `shell_command`
- `arbitrary_command`
- `read_env`
- `read_ssh_keys`
- `read_private_key`
- `delete_files`
- `upload_private_files`
- `open_router_ports`
- `disable_firewall`
- `install_package`
- `curl_pipe_shell`

Blocked and unknown actions fail validation.

## PASS and FAIL Behavior

`scripts/validate-agent-command.py` exits `0` only when every checked command is valid. It exits `1` when any command fails validation.

The report includes:

- Contract result.
- Total command files checked.
- Accepted and blocked counts.
- Approval-required count.
- Mode counts.
- Validation error count.
- Whether sensitive input was blocked.

Validation errors name field paths and classifications only. They do not print raw command targets, service targets, reasons, or parameter values.

## Approval-Required Behavior

Read-only actions must use `read_only`, `dryRun: true`, and `requiresApproval: false`.

`backup_dry_run` must use `dry_run`, `dryRun: true`, and `requiresApproval: false`.

`backup_run` and `restart_allowed_service` must use `approved_write`, `dryRun: false`, `requiresApproval: true`, and `riskLevel: high`.

## What Is Never Exposed

Public repository files and normal reports must not expose:

- Real hosts, IP addresses, URLs, or access methods.
- Tokens, passwords, API keys, secrets, SSH keys, or private keys.
- Private paths, `.env` content, screenshots, uploads, PDFs, logs, or notes.
- Raw `targetDeviceId`, `targetServiceId`, `reason`, or `parameters` values in validation reports.

## Commands

Validate the safe example command files:

```bash
python3 scripts/validate-agent-command.py
```

Validate explicit command files:

```bash
python3 scripts/validate-agent-command.py examples/agent-command.health-check.example.json
```

Validate examples and write the ignored safe runtime report:

```bash
bash scripts/check-agent-command.sh
```

Run the repository doctor without writing the command runtime report:

```bash
bash scripts/doctor.sh
```

## Future Raspberry Pi 8GB Agents

This contract prepares future Raspberry Pi 8GB agents by separating intent from execution. A local AI can request a narrow action using stable IDs and safe parameters, while the Control Plane can reject anything outside the allowlist before a future agent receives work.

The contract also leaves room for small agents to implement only a subset of allowed actions while preserving a shared validation boundary.

## Limitations

- No command is executed in v0.5-local.
- No remote device or local service is contacted.
- JSON Schema is documentation-oriented; the Python validator is the enforcement path.
- Sensitive-pattern blocking is intentionally conservative and may reject text that looks operationally risky.
- Approval recording is not implemented yet.
- Agent identity, policy matching, and device capability discovery are not implemented yet.

## v0.6 Next-Step Idea

v0.6 could add an Agent Policy Engine that maps validated command requests to local policy rules, approved device capability IDs, and explicit approval records before any future execution path exists.
