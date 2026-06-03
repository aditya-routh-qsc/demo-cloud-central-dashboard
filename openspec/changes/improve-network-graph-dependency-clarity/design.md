## Context

The dashboard currently renders a dependency graph from cached ticket and dependency data. Existing graph behavior already distinguishes inter-team versus intra-team classification, but it assumes directional edges, includes all discovered nodes, and relies on the node details panel for some ticket-type context. That makes the graph harder to scan for relation semantics and ticket identity at a glance.

This change stays within the existing frontend-first graph rendering model and does not introduce a new graph library or a new backend service.

## Goals / Non-Goals

**Goals:**
- Represent bidirectional relations, especially `Relates to`, without implying direction.
- Exclude nodes with no dependency edges from the dependency graph surface.
- Make ticket type easier to infer directly in the graph.
- Preserve existing node details and deep-link behavior as a fallback for inspection.

**Non-Goals:**
- Redesigning the overall dashboard layout.
- Replacing Cytoscape or changing the graph layout engine.
- Adding live Jira lookups from the graph view.
- Changing the cached ticket extraction pipeline.

## Decisions

1. Model relation direction explicitly in the graph element data.
- Rationale: the graph needs to know whether a relation is directional or bidirectional before rendering arrowheads.
- Alternatives considered:
  - Infer from label text only: rejected because labels alone are ambiguous and brittle.
  - Hard-code visual exceptions in the renderer: rejected because it couples semantics to presentation too tightly.

2. Render `Relates to` as a bidirectional relation with no arrowheads.
- Rationale: bidirectional semantics are clearer when both endpoints are visually equal.
- Alternatives considered:
  - Keep a single arrow in one direction: rejected because it falsely implies ownership or flow.
  - Use a double-headed arrow: considered, but it still implies directionality and can look cluttered.

3. Filter graph nodes down to tickets participating in at least one edge.
- Rationale: isolated tickets do not help dependency exploration and make the graph harder to read.
- Alternatives considered:
  - Keep isolated nodes with a distinct style: rejected because the requirement is to hide them entirely.
  - Move isolated tickets into a separate list: out of scope for this change.

4. Add stronger ticket-type cues directly to the graph nodes.
- Rationale: some ticket types are not obvious from key-only labels, especially at a glance.
- Alternatives considered:
  - Details-panel-only type display: rejected because it requires a click.
  - Increase node label length significantly: rejected because it reduces graph density and readability.

5. Keep the node details panel as the source of deeper inspection.
- Rationale: the graph should stay concise; detailed metadata belongs in the side panel.
- Alternatives considered:
  - Put full metadata inside each node label: rejected for visual overload.

## Risks / Trade-offs

- [Risk] Hiding isolated nodes can obscure tickets that have no recorded dependencies. -> Mitigation: keep the ticket explorer and details panel available for broader inspection.
- [Risk] Removing arrows from bidirectional relations may reduce contrast with directional dependencies if styling is not distinct enough. -> Mitigation: use consistent edge styling rules and explicit relation labels.
- [Risk] Adding more ticket-type cues can make nodes visually dense. -> Mitigation: keep the cue compact and defer detailed fields to the details panel.
- [Risk] Graph filtering may reduce perceived completeness for users expecting a full ticket inventory. -> Mitigation: document the behavior as a dependency graph, not a full ticket list.

## Migration Plan

1. Update network element data to distinguish directional versus bidirectional relations.
2. Apply edge styling rules so bidirectional relations do not show arrowheads.
3. Filter the graph node set to only nodes referenced by at least one edge.
4. Add or strengthen ticket-type cues in the node rendering path.
5. Update validation checks and manual verification criteria.

Rollback strategy:
- Restore the previous node set and edge arrow behavior if the new graph becomes too sparse or confusing.

## Open Questions

- Should ticket type be shown as a compact badge, a shape, or a secondary label on the node?
- Should the graph include a dedicated legend entry for bidirectional relations?
- Should nodes with no edges remain discoverable through a separate summary list or details panel entry point?
