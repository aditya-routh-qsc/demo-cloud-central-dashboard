## Why

Navigation takes unnecessary horizontal space and does not offer a compact mode for graph-heavy workflows. Operators also lack clear visibility into last update time, and automated sync cadence is hard-coded instead of being configurable via environment settings.

## What Changes

- Add a collapsible sidebar behavior for dashboard navigation.
- In collapsed mode, show only navigation icons; in expanded mode, show icons with labels.
- Preserve active tab behavior and keyboard accessibility across collapsed and expanded states.
- Surface a clear "last update" timestamp in the dashboard shell.
- Introduce configurable environment variable(s) in `.env` for automated scheduled sync and database refresh interval.
- Wire backend scheduler to read the interval from configuration at startup with safe defaults and validation.

## Capabilities

### New Capabilities
- `configurable-sync-schedule-interval`: Allows operators to configure automated sync/database update interval from `.env` without code changes.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extend dashboard navigation and status UI to support collapsible icon-only/sidebar-expanded modes and visible last update time.

## Impact

- Frontend: `frontend/index.html`, `frontend/style.css`, `frontend/app.js` for sidebar toggle control, icon+label states, and last-update display.
- Backend/config: `main.py`, `config_utils.py`, and `.env` handling for scheduler interval configuration and validation.
- Operations: runtime behavior for scheduled sync timing becomes environment-driven.
