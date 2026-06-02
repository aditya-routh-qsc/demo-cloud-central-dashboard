## ADDED Requirements

### Requirement: Multi-Value Status Filter Selection
The dashboard SHALL allow users to select one or more status values simultaneously for ticket, metric, and network data filtering.

#### Scenario: User selects multiple statuses
- **WHEN** a user selects multiple status values in the status filter control
- **THEN** the effective filter state includes all selected statuses and all dashboard views apply the same status set

#### Scenario: User includes Done status explicitly
- **WHEN** Done is present in available status options and the user selects Done
- **THEN** dashboard views include tickets in Done status alongside any other selected status values

### Requirement: Stable Filter Option Discovery
The dashboard SHALL populate status and assignee filter options from the full relevant dataset scope rather than only the currently rendered paginated subset.

#### Scenario: Options remain available under pagination
- **WHEN** a user changes page size or offset in ticket results
- **THEN** status and assignee filter option lists remain stable for the same effective filter scope

#### Scenario: Empty page does not collapse options
- **WHEN** current paginated results are empty but matching records exist in the broader filtered dataset
- **THEN** status and assignee filter controls continue to show available option values instead of degrading to only All
