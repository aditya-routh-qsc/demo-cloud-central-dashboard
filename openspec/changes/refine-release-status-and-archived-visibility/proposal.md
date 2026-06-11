## Why

The Release tab currently allows opening Edit when rows exist even if none are selected, exposes overdue as a standalone status option, and includes archived releases in API/UI payloads. This creates avoidable user friction and inconsistent release visibility semantics.

## What Changes

- Enforce selection-gated Edit action in Release table: Edit remains disabled until one or more checkbox rows are selected.
- Preserve and verify dirty-state behavior for Release modal footer controls so Reset and Apply Changes are disabled until staged changes differ from persisted state.
- Update status semantics so Overdue is not shown as a standalone status option in release table and graph filters; selecting Planned includes both Planned and Overdue records.
- Exclude archived releases from standard release API outputs and all dashboard release UI surfaces, while retaining archived release persistence in the database.

## Capabilities

### New Capabilities
- `release-visibility-and-status-filtering`: Unified release visibility and filter semantics for selection-gated edit actions, planned+overdue grouping, and archived exclusion from dashboard/API.

### Modified Capabilities
- `release-dependency-batch-editing`: Tighten Edit entry gating to require at least one selected row.
- `central-dashboard-frontend-interface`: Refine Release tab status filter and graph filter semantics.

## Impact

- Frontend: `frontend/app.js`, `frontend/index.html`
- Backend/API: `main.py`
- Tests: `tests/test_frontend_team_links.py`, `tests/test_main_team_defaults.py`, `tests/test_main_release_relationship_apply.py`
- Persistence: No database schema changes; archived rows remain stored.
