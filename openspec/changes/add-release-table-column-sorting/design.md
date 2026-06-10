## Context

The Release tab currently shows Jira release rows but uses static table ordering. Users need fast inspection workflows similar to spreadsheet behavior, especially for release-date prioritization where lexical sorting is incorrect for date semantics. This enhancement is scoped to frontend interaction/state logic and must continue using existing backend release retrieval without modifying `services.py`.

## Goals / Non-Goals

**Goals:**
- Add clickable Release table headers with tri-state sort cycles: Ascending, Descending, then Default (unsorted).
- Add visible sort direction indicators on the active header.
- Introduce deterministic frontend sort state management (active column + direction).
- Implement date-aware comparator logic so Release Date sorts chronologically.

**Non-Goals:**
- Changing release API shape or backend fetch logic.
- Adding server-side sorting/query parameters.
- Redesigning other dashboard tabs beyond minimal shared table-header styles if needed.

## Decisions

1. Keep sorting fully client-side over already-loaded Release rows.
Rationale: avoids contract churn and keeps UX responsive.
Alternative: server-side sort params; rejected due to unnecessary backend scope.

2. Represent sort state as `{ columnKey, direction }` where direction is `asc | desc | none`.
Rationale: explicit state simplifies tri-state toggling and render updates.
Alternative: boolean flag plus implicit column memory; rejected as harder to reason about.

3. Derive a sorted view from original rows and preserve a stable unsorted baseline.
Rationale: third click must restore default ordering exactly.
Alternative: mutate source rows in-place; rejected because default restoration becomes error-prone.

4. Use type-specific comparators, including date parsing for Release Date.
Rationale: ensures chronological correctness and avoids plain-string date mistakes.
Alternative: locale string compare for all columns; rejected because date order can be incorrect.

5. Render indicator icons in headers with active-state classes and ARIA-friendly labeling.
Rationale: communicates current sort mode clearly and improves accessibility.
Alternative: text-only status outside header; rejected due to lower discoverability.

## Risks / Trade-offs

- [Risk] Mixed/invalid date strings can lead to inconsistent ordering. -> Mitigation: normalize parse strategy and fallback handling for missing/invalid dates.
- [Risk] Re-render logic may desync indicator state and row order. -> Mitigation: drive both from a single source-of-truth sort state.
- [Trade-off] Client-side sorting means ordering applies only to in-memory dataset. -> Mitigation: acceptable for current Release data volume and tab behavior.