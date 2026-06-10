## Why

The Release tab currently lists Jira releases but cannot capture dependency intent or visualize release relationships, making planning and impact analysis manual and error-prone. This change is needed now to let teams model release-to-release dependencies directly in the dashboard and immediately inspect them in an interactive graph without backend contract churn.

## What Changes

- Add multi-row selection to the Release table through a left-most checkbox column.
- Add a relationship control bar with two searchable multi-select dropdowns and an Apply action:
  - Depends On: set dependency edges for all checked rows.
  - Released Together: set co-release links for all checked rows.
- Persist dependency metadata locally in JSON keyed by Jira release id with:
  - depends_on: array of release ids.
  - co_releases: array of release ids, maintained bidirectionally.
- Add client-side reconciliation (silent scrubbing) that removes stale ids from local relationship data when those ids are absent from the current Jira payload.
- Add a graph panel toggle in the Release tab and render an interactive dependency graph aligned to design/release-dependency-demo.png guidance.
- In graph mode:
  - Group co-releases into shared cluster containers.
  - Omit orphan releases (no dependencies and no co-releases).
  - Provide multi-select status filters (Released, Planned, Archived, Overdue).
  - Apply status color coding aligned with existing dashboard theme.
- Keep services.py release fetching behavior and API shape unchanged; all relationship management remains frontend-driven with local JSON persistence.

## Capabilities

### New Capabilities
- release-dependency-management: Defines release relationship authoring, local JSON schema/persistence rules, reconciliation behavior, and graph rendering/filter requirements for release dependencies.

### Modified Capabilities
- central-dashboard-frontend-interface: Extends Release-tab interaction requirements to include selection checkboxes, relationship controls, graph-panel toggle, and status-filtered dependency visualization.

## Impact

- Frontend: frontend/index.html, frontend/app.js, frontend/style.css for controls, persistence wiring, and graph UI.
- Local data: new persisted JSON artifact for release relationships keyed by release id.
- Docs/specs/tests: new capability spec plus updates to frontend capability and behavior tests.
- Dependency/library: introduce a lightweight graph visualization library compatible with current plain HTML/CSS/JS architecture.
