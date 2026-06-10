## Context

The dashboard already renders release data in the Release tab with filtering and sorting in frontend/app.js, sourced from /api/releases and existing services.py integration. The new behavior must remain frontend-centric and preserve current backend contracts while introducing relationship authoring and dependency visualization. The graph design target references design/release-dependency-demo.png and must remain visually consistent with existing dashboard theming (tokens, panel patterns, status colors).

Constraints:
- Workspace uses plain HTML/CSS/JS frontend patterns (no framework-level state library).
- Release identity must rely on Jira release id, not name.
- Relationship persistence is local JSON and must self-heal when Jira payloads drift.
- Orphan releases (no depends_on and no co_releases) are excluded from graph rendering.

## Goals / Non-Goals

**Goals:**
- Add release table multi-select checkboxes and relationship assignment controls.
- Persist depends_on and co_releases relationships in local JSON keyed by release id.
- Enforce bidirectional integrity for co_releases updates.
- Add graph panel toggle and dependency graph rendering that supports:
  - co-release clustering
  - status-based node coloring
  - multi-select status visibility filters
  - orphan omission
- Add client-side reconciliation that silently scrubs stale ids from local relationship arrays when ids no longer exist in Jira payload.
- Keep implementation aligned with existing dashboard style system and release status color semantics.

**Non-Goals:**
- Changing /api/releases response schema.
- Editing services.py retrieval logic.
- Introducing server-side persistence for release relationships.
- Refactoring unrelated dashboard tabs.

## Decisions

1. Use a dedicated local relationship file keyed by release id.
Rationale: stable id-based mapping survives release-name changes and keeps backend unchanged.
Alternative considered: embed data in query params or localStorage only; rejected for maintainability and reconciliation complexity.

2. Apply relationship edits from table selection to both relationship controls in one commit operation.
Rationale: keeps batch operations deterministic and easier to reason about for users selecting multiple rows.
Alternative: per-row inline editing; rejected due to high interaction overhead.

3. Enforce bidirectional co-release writes and scrubbing through a normalization utility.
Rationale: one utility path guarantees symmetry and consistency during save/load/render.
Alternative: ad-hoc updates in UI handlers; rejected as error-prone.

4. Introduce a lightweight graph library compatible with vanilla JS (Cytoscape.js).
Rationale: supports custom node/edge styles, dynamic filtering, and grouped presentation without framework dependencies.
Alternative: hand-drawn SVG/canvas; rejected due to complexity and maintenance cost.

5. Represent co-release groupings as explicit visual containers (compound nodes/sub-box style).
Rationale: matches demo guidance and improves readability of go-live coupling relationships.
Alternative: color-only grouping; rejected because grouping boundaries are ambiguous.

6. Perform silent reconciliation whenever release payload is loaded and before any save.
Rationale: guarantees stale ids are scrubbed before persistence and before graph/table usage.
Alternative: one-time migration script; rejected because drift can happen repeatedly over time.

## Risks / Trade-offs

- [Risk] Local JSON corruption or malformed content can break graph rendering. -> Mitigation: schema validation with safe defaults and auto-rewrite of normalized structure.
- [Risk] Dense dependency sets can produce cluttered layouts. -> Mitigation: default fit/zoom bounds, status filters, and clustered co-release containers.
- [Risk] Bidirectional co-release maintenance may create accidental cycles or duplicates. -> Mitigation: set-based dedupe and canonical sort on save.
- [Trade-off] Client-only persistence means relationships are per deployment/runtime context. -> Mitigation: document location and enable future backend sync as follow-up.

## Migration Plan

1. Add new relationship persistence module and JSON file bootstrap logic.
2. Integrate selection controls and relationship apply workflow in Release table.
3. Add reconciliation pass on release load and pre-save.
4. Add graph panel UI, status filters, and layout rendering.
5. Validate behavior with updated frontend contract tests and manual graph checks.

Rollback:
- Hide graph panel and relationship controls while preserving existing Release table/list behavior.
- Ignore relationship JSON file at runtime.

## Open Questions

- Should the local JSON file be checked into repository outputs or written to a runtime-specific data directory?
- Should dependency edges be directional-only for depends_on and undirected for co_releases in visual encoding?
- Is drag-and-drop node repositioning in graph view desired now or deferred?
