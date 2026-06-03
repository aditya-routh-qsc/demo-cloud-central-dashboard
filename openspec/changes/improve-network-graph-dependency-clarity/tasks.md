## 1. Dependency Semantics

- [ ] 1.1 Add bidirectional relation handling to the network graph data model.
- [ ] 1.2 Preserve directional semantics for dependencies that are not bidirectional.
- [ ] 1.3 Update edge styling so bidirectional relations render without arrowheads.

## 2. Graph Node Scope

- [ ] 2.1 Filter graph nodes to tickets that participate in at least one dependency edge.
- [ ] 2.2 Ensure connected nodes remain visible after graph filtering and layout.
- [ ] 2.3 Keep node details and ticket explorer paths available for tickets excluded from the graph.

## 3. Ticket Type Visibility

- [ ] 3.1 Add a compact ticket-type cue to graph node presentation.
- [ ] 3.2 Make task and epic nodes visually distinguishable at a glance.
- [ ] 3.3 Preserve node details panel type display as a fallback for deeper inspection.

## 4. Validation and Documentation

- [ ] 4.1 Update API contract documentation to describe bidirectional dependency rendering and connected-node graph scope.
- [ ] 4.2 Extend smoke/contract checks for bidirectional edges, connected-node filtering, and visible ticket-type cues.
- [ ] 4.3 Perform manual desktop verification for relation direction, graph completeness, and ticket-type readability.
