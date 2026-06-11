## ADDED Requirements

### Requirement: Selection-Gated Release Edit Action
The system SHALL disable the Release Edit action until at least one release row is selected via checkbox.

#### Scenario: Edit disabled without selection
- **WHEN** no release rows are selected
- **THEN** the Edit button is disabled and does not open the dependency modal

#### Scenario: Edit enabled with selection
- **WHEN** one or more release rows are selected
- **THEN** the Edit button is enabled and can open the dependency modal

### Requirement: Planned Filter Includes Overdue
The system SHALL treat Overdue as part of Planned filtering semantics in release table and graph filters.

#### Scenario: Overdue not shown as standalone table status option
- **WHEN** release status filter options are rendered
- **THEN** Overdue is not displayed as a standalone selectable option

#### Scenario: Planned table filter includes overdue rows
- **WHEN** user selects Planned in the release status dropdown
- **THEN** rows with status Planned and Overdue are both included

#### Scenario: Planned graph filter includes overdue nodes
- **WHEN** Planned is selected in graph status filtering
- **THEN** nodes whose status is Planned or Overdue are rendered

### Requirement: Archived Releases Hidden From Dashboard/API
The system SHALL exclude archived releases from standard release dashboard/API payloads while retaining archived records in persistence.

#### Scenario: Archived omitted from release API response
- **WHEN** `/api/releases` returns release data
- **THEN** releases marked archived are not present in the response payload

#### Scenario: Archived omitted before relationship active-ID derivation
- **WHEN** release relationship endpoints derive active release IDs from live release payloads
- **THEN** archived releases are excluded from active ID lists and relationship processing scope

#### Scenario: Archived persistence retained
- **WHEN** release snapshots are persisted
- **THEN** archived values are still stored in database for historical retention
