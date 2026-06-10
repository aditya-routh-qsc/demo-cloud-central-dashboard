## ADDED Requirements

### Requirement: Frontend Sort State Management for Release Table
The frontend SHALL maintain explicit sort state for Release table interactions, including active column and direction, and MUST keep table rendering and header indicators synchronized to that state.

#### Scenario: Sort state drives both data order and header visuals
- **WHEN** sort state changes from header interaction
- **THEN** the rendered Release rows and active header indicator update from the same state source

#### Scenario: Default state preserves baseline order
- **WHEN** Release sort direction is set to unsorted
- **THEN** the table renders using the default baseline row order from the loaded release dataset
