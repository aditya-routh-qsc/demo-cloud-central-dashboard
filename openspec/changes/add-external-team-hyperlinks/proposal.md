## Why

Team records in the dashboard currently do not expose or preserve a canonical hyperlink to each team's native Jira profile, which blocks a seamless handoff from dashboard analysis to Jira team management. Adding this now improves operational workflow by reducing navigation friction and ensuring team metadata remains actionable across backend storage and frontend views.

## What Changes

- Capture and persist each team's native Jira profile URL during team metadata synchronization using the format `https://home.atlassian.com/o/{organization_id}/people/team/{team_id}?cloudId={cloud_id}`.
- Ensure SQLite schema and persistence logic retain the team profile link so reruns do not lose the value.
- Expose and consume the team profile link in Teams dashboard and Team Details views.
- Render Team Name as an external hyperlink that opens in a new tab (`target="_blank"`).
- Add clean theme-aligned link styling and a subtle external-link icon near the team title header to signal outbound navigation.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extend team metadata contract and Teams/Team Details rendering behavior to include actionable external team profile links.

## Impact

- Backend: `services.py` team sync extraction and transformation, `database.py` schema/persistence/read paths.
- Database: `dashboard_cache.db` teams table includes and preserves team profile link column values.
- Frontend: Team list/detail rendering in `frontend/app.js` and related styling in `frontend/style.css`.
- UX: Outbound link affordance in team header and team name interactions.
