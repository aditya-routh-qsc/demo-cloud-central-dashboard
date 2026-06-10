## ADDED Requirements

### Requirement: Release Table Multi-Row Selection
The Release table SHALL provide a left-most checkbox column that supports selecting multiple release rows for relationship updates.

#### Scenario: Multi-select release rows
- **WHEN** a user checks multiple release rows in the Release table
- **THEN** those rows remain selected for batch relationship operations until cleared or changed

### Requirement: Release Relationship Control Bar
The Release tab SHALL provide relationship controls with two searchable multi-select dropdowns and an Apply action.

#### Scenario: Configure depends-on relationships
- **WHEN** a user selects one or more rows and chooses values in the Depends On dropdown then clicks Apply
- **THEN** the selected rows update their dependency relationships to match the selected depends-on ids

#### Scenario: Configure released-together relationships
- **WHEN** a user selects one or more rows and chooses values in the Released Together dropdown then clicks Apply
- **THEN** the selected rows update co-release relationships using the selected ids with bidirectional consistency

### Requirement: Release Graph Panel Toggle
The Release tab SHALL include a graph-panel trigger that opens and closes a dedicated dependency visualization panel.

#### Scenario: Open graph panel
- **WHEN** a user activates the graph panel trigger in the Release tab
- **THEN** the Release dependency graph panel is displayed using dashboard-themed UI styling

#### Scenario: Close graph panel
- **WHEN** a user deactivates the graph panel trigger
- **THEN** the graph panel is hidden and the Release table interaction remains available
