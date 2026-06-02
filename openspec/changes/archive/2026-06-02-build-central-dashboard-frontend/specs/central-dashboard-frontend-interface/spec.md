## ADDED Requirements

### Requirement: Unified Global Filters Across Dashboard Views
The dashboard SHALL provide one shared filter model across overview, dependency network, metrics, and ticket explorer views. Filter updates MUST persist while navigating between views during the same session.

#### Scenario: Filter state persists on navigation
- **WHEN** a user applies filter values and switches between dashboard views
- **THEN** the same effective filter state remains active and is reflected consistently in each view's data

#### Scenario: Filter reset propagates everywhere
- **WHEN** a user performs a global filter reset action
- **THEN** all views return to unfiltered state and subsequent API requests omit filter-specific query parameters

### Requirement: Always-Visible Sync Trust Indicator
The dashboard SHALL display sync status persistently in the global header. The status MUST include current runtime state and most recent known run outcome information.

#### Scenario: Running sync is visible immediately
- **WHEN** runtime sync state indicates an active run
- **THEN** the header displays an in-progress status indicator without requiring manual page refresh

#### Scenario: Last run outcome remains visible when idle
- **WHEN** no sync is currently running and persisted run details exist
- **THEN** the header displays the latest run outcome summary for operator trust

### Requirement: Jira Deep-Link Access from Analytical Surfaces
The dashboard SHALL provide external Jira issue links from ticket explorer rows and relevant dependency graph node detail contexts.

#### Scenario: Ticket row opens Jira issue
- **WHEN** a user selects the Jira link action for a ticket row
- **THEN** the browser opens the corresponding Jira issue URL for that ticket key

#### Scenario: Graph node details include Jira navigation
- **WHEN** a user selects a dependency graph node with a resolvable ticket key
- **THEN** the node details panel includes an actionable Jira link for that issue

### Requirement: Mobile Read-Only Summary Mode
For mobile viewport breakpoints, the dashboard SHALL present a read-only summary experience and MUST hide dense desktop interaction modules.

#### Scenario: Mobile layout suppresses heavy interaction views
- **WHEN** the client viewport matches configured mobile breakpoint rules
- **THEN** interactive dependency exploration and full ticket table controls are not presented

#### Scenario: Mobile summary preserves operational clarity
- **WHEN** a mobile user opens the dashboard
- **THEN** the interface displays essential KPI and sync-trust summary information without requiring desktop interactions

### Requirement: Contract-Aligned Data Consumption
The frontend SHALL consume existing backend APIs without requiring endpoint schema changes for initial release.

#### Scenario: Core views map to existing contract payloads
- **WHEN** the dashboard loads overview, metrics, network, and ticket data
- **THEN** requests use currently documented endpoints and the UI renders from documented response fields

#### Scenario: Sync actions use existing manual trigger endpoint
- **WHEN** a user triggers manual sync from the dashboard
- **THEN** the frontend issues a request to the existing manual sync endpoint and updates status using the sync status endpoint
