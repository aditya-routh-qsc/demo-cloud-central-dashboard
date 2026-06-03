## Context

The current dashboard already supports global filters, dependency graph rendering, and assignee-grouped ticket exploration. However, graph semantics are not explicitly explained in the network view, and row-count filtering remains user-managed, which can hide available tickets and reduce trust in what users see. This design introduces deterministic graph semantics and removes user-facing row-count control while preserving backend safety guardrails.

## Goals / Non-Goals

**Goals:**
- Make dependency graph semantics self-explanatory with an always-visible legend on desktop.
- Enforce deterministic visual mappings for node issue type and edge dependency/classification semantics, including unknown fallbacks.
- Ensure multiple dependency types between the same source-target pair render as distinct edges.
- Remove user-managed Rows filter behavior and always request the maximum supported ticket row count.
- Keep backend contract compatibility and existing filter model behavior for status/assignee/search/board.

**Non-Goals:**
- Replacing Cytoscape layout strategy or introducing a new graph rendering library.
- Reworking ticket pagination into infinite scroll.
- Changing Jira extraction payload semantics in `services.py`.
- Redesigning mobile summary mode beyond current scope.

## Decisions

1. Add an in-panel legend for network semantics.
- Rationale: users need immediate decoding for node/edge meaning without trial-and-error.
- Alternatives considered:
  - Tooltip-only explanations: rejected; low discoverability.
  - External documentation only: rejected; too far from the interaction surface.

2. Use deterministic normalization and mapping for graph styles.
- Rationale: stable colors/styles build operator muscle memory across sessions and filter states.
- Alternatives considered:
  - Dynamic colors from observed values: rejected due to unstable interpretation.

3. Preserve separate edges for same source-target when dependency types differ.
- Rationale: collapsing relations hides real dependency semantics and undercounts relationship complexity.
- Alternatives considered:
  - Single collapsed edge with aggregate label: rejected for triage workflows needing explicit relation types.

4. Remove user-facing Rows control; request max supported rows in ticket queries.
- Rationale: row controls introduce accidental under-fetch and inconsistent decision context.
- Alternatives considered:
  - Keep control with higher default: rejected as still error-prone.
  - Hard-remove limit in backend endpoint: rejected to preserve backend guardrail control.

5. Keep backend limit guardrail as authoritative safety constraint.
- Rationale: frontend defaults should maximize visibility, while backend remains final control for resource safety.

## Risks / Trade-offs

- [Risk] Larger default ticket payload may increase initial load time. -> Mitigation: retain existing backend max limit and monitor response times.
- [Risk] Additional graph styles and legend UI add visual density. -> Mitigation: keep legend concise and grouped by semantic type.
- [Risk] Parallel edges can increase graph clutter in high-dependency views. -> Mitigation: maintain current filtering and detail-panel drilldown workflow.
- [Risk] Existing deep links with legacy `limit` query parameter may produce stale URL noise. -> Mitigation: ignore and drop row-count query state during serialization.

## Migration Plan

1. Update frontend filter model to remove Rows input/state and force max ticket limit in requests.
2. Add graph semantic mapping utilities and include required semantic fields in node/edge data.
3. Add desktop legend UI and style rules aligned with graph mappings.
4. Adjust edge identity strategy to preserve distinct dependency-type edges.
5. Update contract/smoke checks and manual verification criteria.

Rollback strategy:
- Revert to previous filter UI and graph styling while preserving backend endpoint guardrails.

## Open Questions

- Should legend remain always expanded, or support a collapse toggle for dense layouts?
- Should unknown dependency types be displayed as a dedicated legend entry when not present in current data?
- Should backend default limit be raised to max immediately or kept as-is with frontend forcing max requests?
