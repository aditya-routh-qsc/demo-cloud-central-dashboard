## ADDED Requirements

### Requirement: Tickets Grouped by Assignee
The ticket explorer SHALL present tickets grouped by assignee identity instead of a single flat list.

#### Scenario: Group sections are rendered per assignee
- **WHEN** ticket data is loaded in the explorer
- **THEN** the UI renders one section per assignee and places each ticket in its assignee section

### Requirement: Unassigned Bucket Is Explicit
The ticket explorer SHALL include a dedicated Unassigned group for tickets without assignee values.

#### Scenario: Ticket without assignee appears in Unassigned
- **WHEN** a ticket has no assignee value
- **THEN** the ticket appears in the Unassigned group and is not omitted from grouped output

### Requirement: Group Ordering by Workload Count
Assignee groups SHALL be ordered by descending workload count to prioritize highest ownership load first.

#### Scenario: Group order reflects ticket counts
- **WHEN** grouped ticket sections are displayed
- **THEN** groups are ordered from highest to lowest ticket count with deterministic tie-breaking
