## MODIFIED Requirements

### Requirement: Unified Global Filters Across Dashboard Views
The dashboard SHALL provide one shared filter model across overview, dependency network, metrics, ticket explorer, and teams views. Filter updates MUST persist while navigating between views during the same session. The shared filter model MUST include Team as a multi-select dimension that cascades assignee options to selected team rosters.

#### Scenario: Filter state persists on navigation
- **WHEN** a user applies filter values and switches between dashboard views
- **THEN** the same effective filter state remains active and is reflected consistently in each view's data

#### Scenario: Filter reset propagates everywhere
- **WHEN** a user performs a global filter reset action
- **THEN** all views return to unfiltered state and subsequent API requests omit filter-specific query parameters

#### Scenario: Team filter cascades assignee options
- **WHEN** team filter selections are updated
- **THEN** assignee filter options are recalculated to selected team members only while preserving valid existing selections

### Requirement: Contract-Aligned Data Consumption
The frontend SHALL consume backend APIs through route contracts served by the existing dashboard backend and SHALL include Teams workspace data retrieval endpoints aligned to cached SQLite-backed data models.

#### Scenario: Core views map to existing contract payloads
- **WHEN** the dashboard loads overview, metrics, network, and ticket data
- **THEN** requests use currently documented endpoints and the UI renders from documented response fields

#### Scenario: Teams view maps to cache-backed contract payloads
- **WHEN** the Teams workspace loads roster, grouped ticket, and timeline data
- **THEN** requests resolve from backend cache-backed contracts without direct Jira API calls from the browser

#### Scenario: Sync actions use existing manual trigger endpoint
- **WHEN** a user triggers manual sync from the dashboard
- **THEN** the frontend issues a request to the existing manual sync endpoint and updates status using the sync status endpoint

## ADDED Requirements

### Requirement: Skeleton Loading States for Dense Analytical Panels
The dashboard SHALL display skeleton loading states for graph and timeline-oriented panels while asynchronous data is resolving.

#### Scenario: Teams timeline displays skeleton placeholders
- **WHEN** a selected team timeline request is pending
- **THEN** timeline skeleton rows are shown until timeline metrics are available

#### Scenario: Graph and timeline panels avoid blank flashes
- **WHEN** panel data transitions between filter changes
- **THEN** skeleton placeholders remain visible until the next valid panel render is complete
