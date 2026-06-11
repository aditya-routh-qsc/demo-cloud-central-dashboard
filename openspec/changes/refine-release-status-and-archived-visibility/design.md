## Context

The Release tab already supports dependency editing, status filtering, and graph rendering. However, Edit activation currently depends on table row availability instead of actual row selection, Overdue appears as an independent status option, and archived releases remain visible in dashboard/API flows.

## Goals / Non-Goals

### Goals
- Disable Edit until at least one release row checkbox is selected.
- Keep modal Reset and Apply Changes disabled by default and enabled only for dirty staged state.
- Remove Overdue as a standalone filter option and include overdue records when Planned is selected.
- Apply planned+overdue grouping consistently in both table and graph filtering logic.
- Exclude archived releases from dashboard/API responses while preserving database storage of archived records.

### Non-Goals
- Removing archived rows from database persistence.
- Redesigning release modal UX beyond button-state behavior.
- Changing release status badges/colors for row presentation.

## Decisions

1. Frontend selection gating: Edit button disabled state includes selected-row count check.
2. Planned/overdue grouping: use matching logic (`status === Planned` includes `row.status === Overdue`) rather than mutating backend status values.
3. Graph filter simplification: expose only Released and Planned options; Planned includes Overdue nodes.
4. Archived exclusion boundary: enforce at API response shaping layer so all dashboard consumers receive non-archived releases by default.

## Risks / Trade-offs

- Risk: Hidden archived records may reduce visibility for users who previously relied on archived status in dashboard.
- Mitigation: Keep archived data persisted in DB so future admin/report endpoints can re-expose archive data explicitly if needed.

## Migration Plan

1. Update frontend release filter/render logic and graph status options.
2. Add backend release payload filtering helper and apply to release endpoints.
3. Update/extend tests for new filtering and selection semantics.
4. Validate via targeted test execution and manual dashboard checks.

## Open Questions

- Should archived releases eventually be exposed in a dedicated admin/archive-only endpoint?
