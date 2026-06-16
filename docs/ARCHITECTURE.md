# Architecture

HomeLab Control Plane v0.1 is a documentation and metadata foundation. It does not run services, manage hosts, scan networks, or expose an application interface.

## Layers

- Device layer: sanitized inventory records for physical or logical devices.
- Service layer: sanitized records for local services and ownership hints.
- Runbook layer: operational references and maintenance procedures.
- Security layer: boundaries for what can and cannot be committed.

## Data Flow

Public repository files contain schemas, fake examples, and documentation. Real inventory data should remain in ignored local files. Future tooling may read local data and render it elsewhere, but this repository should remain safe without requiring external dependencies.

## Design Constraints

- No real addresses or hostnames in committed examples.
- No secrets or private operational artifacts.
- No cloud provider configuration.
- No network scanning behavior.
- No application UI implementation.
