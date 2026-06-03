## ADDED Requirements

### Requirement: Bidirectional Relations Render Without Directional Arrowheads
The dependency graph SHALL render bidirectional relations, including `Relates to`, without arrowheads on either end so the relation is not interpreted as directional.

#### Scenario: Relates to is visually undirected
- **WHEN** the graph contains a dependency whose semantic meaning is bidirectional
- **THEN** the edge is rendered without arrowheads at either end and does not imply a source-to-target flow

#### Scenario: Directional dependencies remain directional
- **WHEN** the graph contains a dependency that is inherently directional
- **THEN** the edge MAY retain directional arrowheads so users can distinguish directed dependencies from bidirectional ones

### Requirement: Dependency Graph Excludes Isolated Tickets
The dependency graph SHALL only display tickets that participate in at least one dependency edge.

#### Scenario: Tickets without edges are hidden from the graph
- **WHEN** a ticket has no incoming or outgoing dependency edges in the active graph scope
- **THEN** the ticket does not appear as a node in the dependency graph

#### Scenario: Connected tickets remain visible
- **WHEN** a ticket participates in at least one dependency edge
- **THEN** the ticket appears as a node in the dependency graph

### Requirement: Ticket Type Is Visible in Graph Node Presentation
The dependency graph SHALL make ticket type visible at the node level so users can distinguish ticket types such as task and epic without opening the node details panel.

#### Scenario: Node presentation exposes ticket type
- **WHEN** a user views a ticket node in the dependency graph
- **THEN** the node presentation includes a visible cue for the ticket type

#### Scenario: Ticket types remain distinguishable at a glance
- **WHEN** the graph contains multiple ticket types such as task and epic
- **THEN** the node presentation makes those types visually distinguishable without requiring a click on the node
