## Why

Pod tracking workflows increasingly share Kanban board links rather than direct ticket IDs, and manual extraction of ticket details from those links is slow and error-prone. This change is needed now so automation can reliably derive ticket metadata from board URLs and feed dashboard/reporting workflows.

## What Changes

- Introduce a capability to accept one or more Kanban board links as input and discover the referenced ticket identifiers.
- Add extraction logic requirements for fetching ticket details for discovered identifiers, including key fields needed for operational tracking.
- Define behavior for invalid/unreachable links and links that resolve to zero tickets.
- Define normalized output contract for discovered tickets and extraction errors so downstream scripts can consume results consistently.
- Add clear operator-facing usage guidance for running the extraction flow with board links.

## Capabilities

### New Capabilities
- `kanban-link-ticket-discovery`: Discover ticket IDs from Kanban board links and return normalized ticket details for automation workflows.

### Modified Capabilities
- None.

## Impact

- Affected code: Script/service layer that currently expects direct ticket inputs.
- Affected external APIs/systems: Kanban board endpoint access and ticket detail API lookups (implementation-specific connector in follow-up tasks).
- Dependencies: May reuse existing HTTP and environment configuration patterns.
- Security and operations: Must preserve credential handling via environment configuration and provide clear partial-error reporting for broken or inaccessible links.
