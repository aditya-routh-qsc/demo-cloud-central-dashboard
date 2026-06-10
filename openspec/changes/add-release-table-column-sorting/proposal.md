## Why

The Release tab currently renders data but does not support interactive sorting, making it harder to analyze releases quickly from the dashboard. Adding spreadsheet-style column sorting now improves usability and decision speed while reusing existing frontend data and backend contracts.

## What Changes

- Add clickable Release table headers that cycle sort mode per column: Ascending -> Descending -> Default (unsorted).
- Add visible sort indicators on headers to show the active sort column and direction.
- Introduce frontend state management for active sort column and direction.
- Add sorting utility functions for text and date-aware comparisons, with true chronological sorting for Release Date.
- Keep sorting fully client-side in frontend UI/state logic and do not modify existing `services.py` retrieval behavior.
- Update behavior documentation and tests to reflect sortable Release table behavior.

## Capabilities

### New Capabilities
- `release-table-column-sorting`: Adds interactive header sorting behavior, visual sort signals, and date-aware sorting logic for Release table data.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extends frontend interaction requirements to include sortable tabular data behavior in the Release view.

## Impact

- Frontend: Release tab table header interactions, sorting state, and table rendering logic in `frontend/`.
- Documentation: behavior spec updates for sortable header UX and chronological date handling.
- Testing: contract tests for header interactivity, indicator states, and date-sort correctness.
- Backend/service contract: no API shape or Jira fetch logic changes; existing release endpoint is consumed as-is.