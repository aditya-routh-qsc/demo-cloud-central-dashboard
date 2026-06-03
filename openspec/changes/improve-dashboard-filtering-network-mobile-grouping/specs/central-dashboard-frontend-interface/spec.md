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

### Requirement: Dependency Graph Legend and Semantic Styling
The desktop dependency graph SHALL provide an always-visible legend that explains node and edge encodings, and SHALL use distinct visual encodings for ticket and dependency semantics.

#### Scenario: Node legend clarifies ticket type encoding
- **WHEN** a user opens the network tab on desktop
- **THEN** the graph panel displays a node legend that maps node colors to ticket issue types and includes an explicit unknown/fallback category

#### Scenario: Edge legend clarifies dependency encoding
- **WHEN** a user opens the network tab on desktop
- **THEN** the graph panel displays an edge legend that maps edge colors to dependency types and includes an explicit unknown/fallback category

#### Scenario: Classification legend clarifies line style meaning
- **WHEN** inter-team and intra-team classifications are present in graph data
- **THEN** the graph panel legend distinguishes line style semantics for classification so users can identify ownership boundaries

#### Scenario: Multiple dependency types between same tickets remain distinct
- **WHEN** more than one dependency record exists between the same source and target ticket pair with different dependency types
- **THEN** the graph renders separate edges for each dependency type rather than collapsing them into one visual edge

#### Scenario: Semantic mappings use existing network payload fields
- **WHEN** the frontend prepares graph elements and styles
- **THEN** node ticket type and edge dependency metadata are derived from existing network response fields without requiring new backend endpoints

#### Scenario: Node color mapping is deterministic by normalized issue type
- **WHEN** node issue type values are rendered in the desktop dependency graph
- **THEN** issue type values are normalized (trimmed and case-insensitive) and mapped to a deterministic color palette for `bug`, `story`, `task`, `epic`, and `sub-task`

#### Scenario: Edge color mapping is deterministic by normalized dependency type
- **WHEN** edge dependency type values are rendered in the desktop dependency graph
- **THEN** dependency type values are normalized (trimmed and case-insensitive) and mapped to a deterministic color palette for `blockers`, `blocks`, `depends_on`, `relates_to`, and `duplicates`

#### Scenario: Classification line style mapping is explicit
- **WHEN** edge classification values are rendered
- **THEN** `inter_team` edges use dashed line styling and `intra_team` edges use solid line styling

#### Scenario: Unknown semantic values use explicit fallback styles
- **WHEN** node issue type or edge dependency/classification values are missing or unrecognized
- **THEN** the graph applies explicit unknown fallback styles and the legend includes those fallback categories
