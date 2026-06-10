## ADDED Requirements

### Requirement: Release Tab Is Available in Dashboard Navigation
The dashboard SHALL provide a `Release` tab as part of the primary dashboard navigation set.

#### Scenario: User can access Release tab
- **WHEN** the dashboard shell renders available tabs
- **THEN** a `Release` tab is presented and can be selected like other primary views

### Requirement: Release Table Renders Jira Release Data
The Release tab SHALL render a table of Jira release data using backend-provided records and MUST display Release Name, Release Date, and Status columns.

#### Scenario: Release table displays returned records
- **WHEN** the frontend receives one or more release records from the existing backend release endpoint
- **THEN** the Release tab table shows one row per release and maps name, date, and status fields to visible columns

#### Scenario: Empty state is shown when no releases exist
- **WHEN** the release endpoint responds successfully with zero records
- **THEN** the Release tab displays an explicit empty-state message instead of a blank table

#### Scenario: Error state is shown for failed release retrieval
- **WHEN** the release endpoint request fails or returns a non-success outcome
- **THEN** the Release tab displays an error state that indicates release data could not be loaded
