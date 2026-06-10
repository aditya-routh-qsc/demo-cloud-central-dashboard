## ADDED Requirements

### Requirement: Release Table Headers Support Tri-State Sorting
The Release table SHALL allow users to click sortable column headers and cycle sort mode for that column in this order: ascending, descending, then unsorted default.

#### Scenario: Header click cycles sort states
- **WHEN** a user clicks the same sortable Release header repeatedly
- **THEN** the table sort state cycles `asc -> desc -> none` and row order updates for each state

#### Scenario: Switching columns resets active sort target
- **WHEN** a user clicks a different sortable Release header
- **THEN** the newly selected column becomes active with ascending sort as the first state

### Requirement: Release Date Sorting Is Chronological
The Release Date column MUST be sorted using date-aware comparison logic rather than plain text comparison.

#### Scenario: Date column sorts oldest to newest in ascending mode
- **WHEN** Release Date is sorted ascending
- **THEN** rows are ordered in true chronological sequence from earliest to latest date

#### Scenario: Date column sorts newest to oldest in descending mode
- **WHEN** Release Date is sorted descending
- **THEN** rows are ordered in true chronological sequence from latest to earliest date

### Requirement: Sort Indicators Reflect Active Header State
The Release table SHALL provide visual indicators on headers showing which column is actively sorted and in which direction.

#### Scenario: Active header shows direction indicator
- **WHEN** a Release column is in ascending or descending mode
- **THEN** the corresponding header displays an active sort indicator matching the current direction

#### Scenario: Unsorted mode clears active indicator
- **WHEN** a header returns to unsorted mode
- **THEN** no active direction indicator remains applied for that column