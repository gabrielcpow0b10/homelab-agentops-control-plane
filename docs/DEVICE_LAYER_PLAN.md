# Device Layer Plan

The device layer describes lab assets using stable, sanitized metadata. It should support planning, maintenance status, and ownership relationships without exposing sensitive operational details.

## v0.1 Fields

- `id`
- `name`
- `type`
- `role`
- `status`
- `location`
- `hostHint`
- `ipHint`
- `accessMethod`
- `notes`
- `securityNotes`
- `runbook`
- `createdAt`
- `updatedAt`

## Device Types

Allowed device types are defined in [device.schema.json](../schemas/device.schema.json).

## Safety Rules

Use generic names and sanitized hints in committed examples. Keep real hostnames, addresses, and access details in ignored local inventory files.
