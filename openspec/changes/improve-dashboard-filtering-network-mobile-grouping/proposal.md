## Why

The current dashboard behavior makes key operational workflows difficult: users cannot reliably include Done tickets in analysis, filter controls can appear empty or unstable, network insights are not usable on mobile, and ticket triage is slowed by a flat ungrouped table. This change is needed to improve trust in data visibility and make workload analysis faster across desktop and mobile experiences.

## What Changes

- Add multi-value status filtering so users can explicitly choose one or more status types, including Done when present in the dataset.
- Improve filter option population so status and assignee choices are sourced from the relevant dataset scope rather than only the currently rendered page subset.
- Provide mobile-optimized dependency insight through a simplified summary experience instead of the full interactive graph canvas.
- Add explicit network empty-state messaging for no-data, hidden-mobile, and load-failure cases.
- Group tickets by assignee in the Tickets view, including an explicit Unassigned group, sorted by workload count.

## Capabilities

### New Capabilities
- `dashboard-filter-option-stability`: Defines stable option discovery behavior for multi-value status/assignee filtering and dataset-scope option sourcing.
- `dashboard-assignee-grouped-ticket-explorer`: Defines grouped ticket presentation by assignee, with Unassigned handling and workload-based ordering.
- `dashboard-mobile-dependency-summary`: Defines mobile dependency summary behavior and graph fallback messaging.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extend filtering, network presentation, and ticket-explorer requirements to support multi-select status behavior, mobile dependency summaries, and grouped ticket workflows.

## Impact

- Affected frontend modules: `frontend/index.html`, `frontend/app.js`, and `frontend/style.css`.
- Likely affected backend API behavior in `main.py` for filter metadata and/or grouped ticket response shaping.
- API contract documentation updates in `docs/API_CONTRACT_SHEET.md`.
- Smoke/contract validation updates in `scratch/smoke_frontend_contract.py`.
