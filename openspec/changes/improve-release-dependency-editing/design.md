## Context

The Release tab already supports multi-row selection, filtering, and sorting, and currently stores release relationship data for visualization workflows. The requested feature introduces a safer batch-edit flow so users can stage dependency changes for multiple selected releases, review two directional relationship views, and commit changes only on explicit apply.

Constraints:
- Must align with existing dashboard visual style and interaction conventions.
- Must preserve current Release tab filtering/sorting/selection behavior.
- No persistence is allowed before Apply Changes.
- Apply must be transactional and rollback on failure.

## Goals / Non-Goals

**Goals:**
- Add an Edit action in Release tab that opens a dependency-edit modal for selected releases.
- Support two editable directional tabs: Depends On and Depended By.
- Support staged add/remove edits, with dirty tracking and disabled/enabled footer actions.
- Commit staged edits with all-or-nothing persistence and loading/error handling.
- Provide Reset to restore modal data from persisted truth.
- Ensure accessibility behavior for modal focus management and keyboard navigation.

**Non-Goals:**
- Redesigning unrelated dashboard tabs.
- Persisting partial edits prior to Apply Changes.
- Changing release table semantics beyond dependency editing.

## Decisions

1. Staged edit model separated from persisted snapshot.
- Rationale: Enables non-destructive add/remove editing and exact Reset semantics.
- Alternative considered: immediate persistence per row action; rejected because it violates requested staged workflow.

2. Union relationship aggregation across selected releases.
- Rationale: Matches user intent to edit dependencies for multiple rows at once while preserving attribution context via tooltip mapping.
- Alternative considered: intersection-only view; rejected due to reduced discoverability and edit coverage.

3. Dual-direction tabs remain editable with synchronization rules.
- Rationale: Users can work from either directional perspective while data remains internally consistent.
- Alternative considered: one tab read-only; rejected because it limits workflow flexibility.

4. Add Dependency panel stages selections without persistence.
- Rationale: Submit in Add panel is an intra-modal state commit only; database writes happen only at Apply Changes.
- Alternative considered: Add panel writes immediately; rejected because it breaks Apply gate requirement.

5. Transactional apply contract.
- Rationale: All staged operations for selected releases are committed atomically; failures rollback all changes.
- Alternative considered: partial success updates; rejected by explicit requirement.

6. Deterministic dirty-state controls.
- Rationale: Reset and Apply buttons are disabled when staged state equals persisted snapshot, enabled only after net changes.
- Alternative considered: enable once user interacts; rejected because it can show actionable state without real changes.

## Risks / Trade-offs

- [Risk] Large release datasets may make modal union tables dense and harder to scan. -> Mitigation: keep searchable add flow, preserve sort order hints, and include clear empty states.
- [Risk] Direction synchronization can introduce subtle duplicates. -> Mitigation: normalize staged relationships by set semantics before rendering and before apply.
- [Risk] Concurrent edits from another session may cause stale snapshot apply conflicts. -> Mitigation: re-read persisted state before apply and fail safely with retry guidance.

## Migration Plan

1. Add Release-tab Edit button and modal shell with tabs, table scaffolding, and footer controls.
2. Introduce staged relationship state, persisted snapshot baseline, and dirty-state computation.
3. Implement row remove and Add Dependency panel behaviors for staged updates.
4. Add apply pipeline with loading state, transactional backend update, success/failure feedback, and rollback behavior.
5. Implement Reset to reload database truth and clear dirty state.
6. Add accessibility wiring and test coverage for keyboard/focus behavior and regression stability.

Rollback:
- Hide Edit button and modal entrypoint behind feature switch or remove wiring while preserving existing Release tab behavior.

## Open Questions

- Should apply endpoint return per-release delta metadata for richer success toasts, or is simple success/failure sufficient for first iteration?
- Should tooltip copy show release identifiers in addition to names for duplicate-name edge cases?
