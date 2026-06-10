## Why

The dashboard currently has no dedicated view for Jira release metadata, even though backend service functions already provide release-date data. Adding a Release tab now closes this frontend visibility gap without changing stable backend fetching logic.

## What Changes

- Add a new `Release` navigation item/tab in the existing dashboard shell.
- Add a Release table view that renders Jira release rows with at least: Release Name, Release Date, and Status.
- Integrate frontend data loading with existing backend endpoints backed by `services.py` release-fetching functions.
- Define loading, empty, and error states for the Release table to keep dashboard behavior consistent.
- Update behavior documentation so `docs/CURRENT_BEHAVIOR_SPEC.md` reflects the new tab and data flow.

## Capabilities

### New Capabilities
- `release-tab-dashboard-view`: Introduces a dedicated dashboard tab and table experience for Jira release data.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Expands dashboard navigation and tab content behavior to include the new Release surface.

## Impact

- Frontend: dashboard navigation/tab composition and data-table rendering logic in `frontend/`.
- Backend integration surface: existing release data endpoint contract (consumed, not reimplemented).
- Documentation: `docs/CURRENT_BEHAVIOR_SPEC.md` requires updates to stay aligned with implemented behavior.
- Testing: frontend tab rendering and release data contract/shape validation should be covered.