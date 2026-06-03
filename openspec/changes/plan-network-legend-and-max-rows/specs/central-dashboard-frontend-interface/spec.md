## ADDED Requirements

### Requirement: Dependency Graph Legend and Semantic Styling
The desktop dependency graph SHALL display an always-visible legend and SHALL apply deterministic semantic styling for nodes and edges.

#### Scenario: Node legend is visible and meaningful
- **WHEN** a user opens the network tab on desktop
- **THEN** the graph panel displays a node legend mapping ticket issue types to node colors, including an explicit unknown fallback category

#### Scenario: Edge legend is visible and meaningful
- **WHEN** a user opens the network tab on desktop
- **THEN** the graph panel displays an edge legend mapping dependency types to edge colors and classification semantics to line styles

#### Scenario: Deterministic normalization drives graph styles
- **WHEN** issue type and dependency fields vary in casing or whitespace
- **THEN** graph styling normalizes values and applies a deterministic mapping with explicit unknown fallback styles

### Requirement: Distinct Edge Rendering for Multiple Dependency Types
The dependency graph SHALL render separate edges for different dependency types between the same source and target ticket pair.

#### Scenario: Multiple relations remain visible
- **WHEN** two or more dependency records exist between the same source and target with different dependency types
- **THEN** each dependency type is rendered as a distinct edge and is not collapsed into a single relation

### Requirement: Fixed Maximum Ticket Rows in Filtered Retrieval
The dashboard SHALL remove user-managed row-count filtering and SHALL request tickets using the maximum supported row limit.

#### Scenario: Rows control is removed from filters
- **WHEN** a user views the global filter controls
- **THEN** no Rows/page-size input is presented as a user-editable filter

#### Scenario: Ticket retrieval ignores user row-count input
- **WHEN** filtered ticket requests are issued
- **THEN** request parameters use the maximum supported row limit and do not rely on user-provided row-count state

#### Scenario: URL state excludes row-count filter parameter
- **WHEN** filter state is serialized to or restored from the URL
- **THEN** row-count is not represented as a user-adjustable filter parameter
