## ADDED Requirements

### Requirement: Release Relationship JSON Schema
The system SHALL persist release relationships in local JSON keyed by Jira release id, where each release entry contains `depends_on` and `co_releases` arrays of release ids.

#### Scenario: Persisting dependency relationships
- **WHEN** a user applies relationship updates for selected release rows
- **THEN** the local JSON stores selected dependency ids in the target release entry under `depends_on`

#### Scenario: Persisting co-release relationships
- **WHEN** a user applies released-together updates for selected release rows
- **THEN** the local JSON stores selected co-release ids under `co_releases` and excludes duplicates

### Requirement: Co-Release Bidirectional Integrity
The system MUST maintain co-release relationships bidirectionally in persisted data.

#### Scenario: Co-release update mirrors both directions
- **WHEN** release A is saved with release B in `co_releases`
- **THEN** release B is automatically saved with release A in `co_releases`

#### Scenario: Co-release removal mirrors both directions
- **WHEN** a previously linked co-release relationship is removed between release A and release B
- **THEN** both release entries remove the opposite id from `co_releases`

### Requirement: Silent Scrubbing For Desynchronized IDs
The system MUST reconcile local relationship JSON against the current Jira release payload and silently scrub ids that no longer exist.

#### Scenario: Stale id removed before render
- **WHEN** relationship JSON contains an id absent from the latest Jira release payload
- **THEN** the stale id is removed from all `depends_on` and `co_releases` arrays before table or graph rendering

#### Scenario: Stale id removed before save
- **WHEN** relationship updates are saved while relationship JSON still contains missing Jira ids
- **THEN** the save pipeline removes stale ids and writes only ids present in the current Jira release dataset

### Requirement: Dependency Graph Visibility Rules
The graph view SHALL render only releases participating in at least one dependency relationship and SHALL group co-release sets in dedicated cluster containers.

#### Scenario: Omit orphan releases from graph
- **WHEN** a release has no `depends_on` entries and no `co_releases` entries
- **THEN** that release is not rendered as a graph node

#### Scenario: Co-release cluster rendering
- **WHEN** two or more releases are linked through `co_releases`
- **THEN** the graph renders them inside a shared co-release grouping container

### Requirement: Graph Status Filters
The graph view MUST provide a multi-select status filter that controls node visibility by release status.

#### Scenario: Hide filtered-out statuses
- **WHEN** a user deselects one or more statuses in graph filters
- **THEN** nodes with those statuses are hidden from graph rendering

#### Scenario: Restore filtered statuses
- **WHEN** a user reselects a previously deselected status
- **THEN** nodes with that status are rendered again if they satisfy relationship visibility rules

### Requirement: Graph Node Status Colors
The graph view SHALL style node colors by release status using dashboard-aligned theme colors.

#### Scenario: Status color mapping in graph nodes
- **WHEN** graph nodes render for statuses Released, Planned, Archived, and Overdue
- **THEN** nodes use green, light blue, dark orange, and bright red styles respectively for the matching status
