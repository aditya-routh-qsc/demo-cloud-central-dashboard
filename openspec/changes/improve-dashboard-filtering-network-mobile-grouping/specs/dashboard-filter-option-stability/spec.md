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

### Requirement: Fixed Maximum Ticket Rows for Filtered Retrieval
The dashboard SHALL remove user-managed row-count filtering and SHALL request tickets at the maximum supported row limit for each filtered retrieval.

#### Scenario: Rows filter control is not user-visible
- **WHEN** a user opens the global filter section
- **THEN** no Rows/page-size input is presented as part of interactive filter controls

#### Scenario: Ticket retrieval uses max supported rows
- **WHEN** the dashboard issues filtered ticket retrieval requests
- **THEN** requests use the maximum supported ticket limit rather than a user-provided row-count value

#### Scenario: URL state omits user-managed row-count parameter
- **WHEN** filter state is serialized to or restored from URL query state
- **THEN** row-count values are not represented as user-adjustable filter parameters
