## Context

The dashboard currently renders from cached ticket, metrics, and dependency APIs, but filter behavior and ticket exploration are constrained by page-scoped option discovery and flat tabular output. Users need stronger operational trust: predictable filter controls, explicit inclusion of status categories such as Done, and usable dependency visibility on mobile devices where the full graph is intentionally hidden.

The existing frontend capability already defines global filters, sync visibility, and mobile summary constraints. This design extends those behaviors while preserving the same backend-first architecture (FastAPI + SQLite cache) and avoiding unnecessary data-fetch coupling to external Jira latency.

## Goals / Non-Goals

**Goals:**
- Provide multi-value status selection behavior that allows explicit inclusion/exclusion of statuses.
- Ensure status and assignee filter options are stable and sourced from a broader relevant dataset scope than the currently rendered page subset.
- Improve mobile network usability through summary-first dependency insights and clear empty-state reasoning.
- Present ticket data grouped by assignee, including Unassigned, sorted by workload count.
- Keep interactions consistent with existing global filter model and URL-state persistence expectations.

**Non-Goals:**
- Replacing the desktop interactive graph layout engine.
- Introducing live Jira calls from frontend views.
- Building advanced analytics ranking models beyond count-based workload ordering in this change.
- Redesigning authentication, tenancy, or scheduler infrastructure.

## Decisions

1. Multi-value status filtering at the UI and API query layer.
- Rationale: Explicit user control over status inclusion avoids hidden assumptions about Done visibility and aligns with operational filtering workflows.
- Alternatives considered:
  - Always include Done: rejected because users often need focused active-work views.
  - Single-select status: rejected because it forces repetitive toggling and weakens comparative analysis.

2. Filter option sourcing from full relevant dataset scope, not current page slice.
- Rationale: Page-scoped options can collapse to All-only or incomplete sets under tight filters or pagination, creating trust issues.
- Alternatives considered:
  - Keep page-scoped options: rejected for unstable UX.
  - Hard-coded status list: rejected because teams and workflows differ by board.

3. Mobile dependency summary replaces heavy graph interaction.
- Rationale: Full graph interactions are low-utility at small viewports; summary cards and concise lists preserve insight with better readability and performance.
- Alternatives considered:
  - Keep interactive graph on mobile: rejected due to density and interaction friction.
  - Hide dependency insight entirely on mobile: rejected because operational context is still needed.

4. Tickets grouped by assignee with explicit Unassigned bucket and workload-based ordering.
- Rationale: Grouped views align with triage and ownership workflows better than flat lists.
- Alternatives considered:
  - Flat table only: rejected for poor ownership scanability.
  - Group by status first: rejected as secondary to ownership-driven triage goals.

5. Explicit network empty-state taxonomy.
- Rationale: Users need to distinguish no-data, mobile-summary-mode, and load/dependency failures to avoid misinterpretation.
- Alternatives considered:
  - Generic empty message: rejected as too ambiguous.

## Risks / Trade-offs

- [Risk] More complex filter model increases UI state synchronization complexity. -> Mitigation: Keep one canonical filter state object and deterministic serialization/deserialization to URL query.
- [Risk] Full-scope option fetching could increase payload size if implemented naively. -> Mitigation: Return compact distinct option metadata rather than full ticket records.
- [Risk] Grouped tickets may obscure row-level sorting expectations from current users. -> Mitigation: Provide clear group headers and deterministic item order within groups.
- [Risk] Mobile summary may omit details some users expect from desktop graph. -> Mitigation: Include key dependency counters and top blockers with explicit desktop handoff guidance.

## Migration Plan

1. Add or adapt API contract fields needed for stable filter metadata and grouped ticket presentation.
2. Update frontend filter controls to support multi-value status and assignee behavior.
3. Introduce mobile dependency summary rendering and explicit network empty states.
4. Update smoke/contract checks to validate filter option behavior and grouped ticket output expectations.
5. Rollout behind existing dashboard route with no endpoint removal.

Rollback strategy:
- Revert to prior flat table and single-value filter behavior while retaining cached API compatibility.
- Keep previous mobile suppression behavior as fallback if summary rendering regresses.

## Open Questions

- Should grouped ticket sections be collapsed by default or expanded by default?
- Should workload ordering be count-only in this phase or support optional story-point weighting?
- Should status option lists include statuses absent from current cache but known historically?
