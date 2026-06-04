## ADDED Requirements

### Requirement: Cascading Multi-Select Team Filter
The dashboard SHALL provide a multi-select Team filter in the global filter suite, and selected teams SHALL constrain ticket scope to members of those teams.

#### Scenario: Team selection constrains ticket scope
- **WHEN** one or more teams are selected in the Team filter
- **THEN** all active views show tickets assigned to members of the selected teams only

#### Scenario: Clearing team filter restores unrestricted team scope
- **WHEN** all selected team values are removed
- **THEN** ticket queries return to non-team-constrained behavior

### Requirement: Assignee Filter Cascades from Team Selection
The Assignee filter SHALL cascade based on selected teams and SHALL support quick select-all and clear-all controls for the filtered roster.

#### Scenario: Assignee options collapse to selected team rosters
- **WHEN** one or more teams are selected
- **THEN** the Assignee options list contains only members belonging to selected teams

#### Scenario: Quick roster toggles apply filtered assignees
- **WHEN** a user activates select-all or clear-all on the cascaded assignee roster
- **THEN** assignee selections are updated in a single action without manual per-member selection

### Requirement: Team then Member Hierarchical Ticket Grouping
The Tickets view SHALL render ticket data in a strict hierarchy grouped first by team and then by member.

#### Scenario: Top-level team accordion groups are rendered
- **WHEN** grouped ticket data is available for the active filters
- **THEN** tickets are displayed under collapsible team headers rather than a flat list

#### Scenario: Team headers include summary badges
- **WHEN** a team group header is rendered
- **THEN** it displays inline counts for total tickets, in-progress tickets, and blocked tickets

#### Scenario: Nested member sections appear within expanded team groups
- **WHEN** a team accordion is expanded
- **THEN** tickets are further grouped by assignee/member sections under that team only

### Requirement: JOIN-Based Team Filter Querying
Team-filtered and grouped ticket responses SHALL be produced through relational JOIN-based queries between teams, team_members, and ticket tables without per-team repeated query loops.

#### Scenario: Backend query path avoids N+1 behavior
- **WHEN** team-grouped data is requested
- **THEN** the backend uses set-oriented JOIN queries and returns aggregated results without issuing one query per team

#### Scenario: Grouping payload includes team and member aggregates
- **WHEN** the grouped ticket API responds
- **THEN** the payload includes computed group metrics needed to render team and member sections without client-side recomputation from raw rows
