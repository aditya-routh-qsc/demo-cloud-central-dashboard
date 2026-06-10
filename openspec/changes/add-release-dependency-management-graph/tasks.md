## 1. Release Data Model And Persistence

- [x] 1.1 Add release relationship state model in frontend/app.js for selected row ids, dependency selections, co-release selections, and graph filter selections
- [x] 1.2 Define local JSON schema keyed by Jira release id with depends_on and co_releases arrays and add safe defaults
- [x] 1.3 Implement load/save utilities for local relationship JSON and wire persisted state bootstrap on Release tab load
- [x] 1.4 Implement normalization utility that deduplicates ids, removes self-links, and enforces bidirectional co_releases updates
- [x] 1.5 Implement silent scrubbing utility that removes ids not present in current Jira release payload before render and before save

## 2. Release Table Selection And Relationship Controls

- [x] 2.1 Add a far-left checkbox column to the Release table header/body with row selection state synchronization
- [x] 2.2 Add a relationship control bar in the Release tab with searchable multi-select fields for Depends On and Released Together
- [x] 2.3 Populate both relationship selectors from current release dataset using release id as option value and release name as label
- [x] 2.4 Add Apply action handler that writes depends_on and co_releases for all checked rows and persists normalized JSON
- [x] 2.5 Prevent invalid relationship writes (self-reference) and show non-blocking inline feedback when no rows are selected

## 3. Graph Panel And Visualization Engine

- [x] 3.1 Add graph panel toggle/button in Release tab layout and panel container structure aligned with dashboard panel patterns
- [x] 3.2 Install and integrate a lightweight graph library compatible with vanilla frontend architecture (Cytoscape.js)
- [x] 3.3 Transform release + relationship data into graph nodes/edges using design/release-dependency-demo.png layout guidance
- [x] 3.4 Implement co-release grouping containers/compound nodes to visually cluster releases linked in co_releases
- [x] 3.5 Enforce orphan omission rule so releases with no depends_on and no co_releases are excluded from graph rendering

## 4. Graph Filters And Status Visual Design

- [x] 4.1 Add graph status multi-select filter control for Released, Planned, Archived, and Overdue
- [x] 4.2 Apply status filter state to graph rendering so deselected statuses are hidden and reselected statuses are restored
- [x] 4.3 Add status-based node styles in graph panel: Released green, Planned light blue, Archived dark orange, Overdue bright red
- [x] 4.4 Align graph panel and controls with existing dashboard theme tokens, typography, borders, and focus interactions

## 5. Release Tab Integration And Behavior Safety

- [x] 5.1 Ensure table sorting and table filtering continue to work with checkbox column and relationship controls
- [x] 5.2 Ensure graph panel state and relationship controls refresh correctly after /api/releases reload and tab re-entry
- [x] 5.3 Keep backend behavior unchanged by confining dependency logic to frontend and local JSON persistence only

## 6. Validation And Documentation

- [x] 6.1 Add or update frontend contract tests for checkbox selection and batch relationship apply behavior
- [x] 6.2 Add or update tests for JSON schema persistence, co_releases bidirectionality, and stale-id silent scrubbing
- [x] 6.3 Add or update tests for graph node omission, co-release grouping presence, status filters, and status color mappings
- [x] 6.4 Update docs/CURRENT_BEHAVIOR_SPEC.md with relationship controls, local JSON schema expectations, and graph-panel behavior
- [x] 6.5 Run targeted unittest suites and record validation output for Release-tab dependency features
