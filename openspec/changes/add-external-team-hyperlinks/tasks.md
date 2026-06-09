## 1. Backend Team Link Persistence

- [x] 1.1 Add/verify a `team_profile_url` column in the `teams` SQLite schema and migration guards in `database.py`.
- [x] 1.2 Update Jira team extraction logic in `services.py` to capture upstream team profile URL or synthesize `https://home.atlassian.com/o/{organization_id}/people/team/{team_id}?cloudId={cloud_id}`.
- [x] 1.3 Update team upsert statements to write and preserve `team_profile_url` on conflict updates.
- [x] 1.4 Ensure team read/response shaping includes `team_profile_url` for frontend consumption.

## 2. Frontend Hyperlink Rendering

- [x] 2.1 Update Teams dashboard list rendering in `frontend/app.js` so Team Name is an anchor when `team_profile_url` exists.
- [x] 2.2 Update Team Details header rendering in `frontend/app.js` to display Team Name as an external hyperlink with `target="_blank"` and `rel="noopener noreferrer"`.
- [x] 2.3 Add a subtle external-link icon next to the team title/header and keep it visually aligned with current theme.
- [x] 2.4 Add/adjust styles in `frontend/style.css` for team link color, hover, focus-visible state, and icon spacing.

## 3. Validation and Regression Safety

- [x] 3.1 Add/update backend tests to verify `team_profile_url` persistence and upsert behavior across reruns.
- [x] 3.2 Add/update frontend checks to verify clickable team name behavior in both Teams list and Team Details contexts.
- [x] 3.3 Run targeted test suites and smoke-check desktop/mobile rendering to confirm no regressions.
- [x] 3.4 Document usage/behavior updates in relevant runbook or dashboard docs if UI behavior changes are user-visible.
