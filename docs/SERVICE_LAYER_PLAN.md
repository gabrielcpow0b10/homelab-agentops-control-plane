# Service Layer Plan

The service layer describes local services in a way that can later be mapped to devices, runbooks, and UI views.

## v0.1 Fields

- `id`
- `name`
- `type`
- `status`
- `ownerDeviceId`
- `localUrlHint`
- `portHint`
- `notes`
- `securityNotes`
- `createdAt`
- `updatedAt`

## Safety Rules

Committed service examples must use fake names, generic URLs, and sanitized port hints. Real endpoints belong in ignored local files.

## Future Work

- Add service dependency mapping.
- Add health status metadata.
- Add read-only export format for a future console integration.
