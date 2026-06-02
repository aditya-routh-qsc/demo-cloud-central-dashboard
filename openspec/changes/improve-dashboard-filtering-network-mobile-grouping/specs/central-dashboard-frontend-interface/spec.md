## MODIFIED Requirements

### Requirement: Unified Global Filters Across Dashboard Views
The dashboard SHALL provide one shared filter model across overview, dependency network, metrics, and ticket explorer views. Filter updates MUST persist while navigating between views during the same session. The shared model SHALL support multi-value status selection and consistent status/assignee option behavior across views.

#### Scenario: Filter state persists on navigation
- **WHEN** a user applies filter values and switches between dashboard views
- **THEN** the same effective filter state remains active and is reflected consistently in each view's data

#### Scenario: Filter reset propagates everywhere
- **WHEN** a user performs a global filter reset action
- **THEN** all views return to unfiltered state and subsequent API requests omit filter-specific query parameters

#### Scenario: Multi-value status selection is preserved
- **WHEN** a user selects multiple status values including optional Done
- **THEN** the global filter model preserves the complete selected set across tab navigation and refresh-derived state restoration

### Requirement: Mobile Read-Only Summary Mode
For mobile viewport breakpoints, the dashboard SHALL present a read-only summary experience and MUST hide dense desktop interaction modules.

#### Scenario: Mobile layout suppresses heavy interaction views
- **WHEN** the client viewport matches configured mobile breakpoint rules
- **THEN** interactive dependency exploration and full ticket table controls are not presented

#### Scenario: Mobile summary preserves operational clarity
- **WHEN** a mobile user opens the dashboard
- **THEN** the interface displays essential KPI and sync-trust summary information without requiring desktop interactions

#### Scenario: Mobile dependency summary remains informative
- **WHEN** dependency data is present for the active filter state
- **THEN** the mobile experience surfaces dependency summary signals without requiring the desktop graph canvas

### Requirement: Contract-Aligned Data Consumption
The frontend SHALL consume existing backend APIs without requiring endpoint schema changes for initial release.

#### Scenario: Core views map to existing contract payloads
- **WHEN** the dashboard loads overview, metrics, network, and ticket data
- **THEN** requests use currently documented endpoints and the UI renders from documented response fields

#### Scenario: Sync actions use existing manual trigger endpoint
- **WHEN** a user triggers manual sync from the dashboard
- **THEN** the frontend issues a request to the existing manual sync endpoint and updates status using the sync status endpoint

#### Scenario: Filter and grouping surfaces follow documented contract
- **WHEN** the dashboard initializes filter options and grouped ticket explorer sections
- **THEN** the frontend behavior maps to documented API fields and does not infer required values from paginated view slices alone
