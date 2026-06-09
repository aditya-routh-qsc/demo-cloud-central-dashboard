## Context

The dashboard already synchronizes Jira team metadata into SQLite and renders teams in the frontend, but it does not guarantee preservation or display of a canonical Jira-native team profile link. The new requirement spans backend extraction (`services.py`), persistence (`database.py`/`dashboard_cache.db`), and frontend rendering (`frontend/app.js`, `frontend/style.css`) so operators can open official Jira team pages directly from dashboard team views.

## Goals / Non-Goals

**Goals:**
- Persist a canonical team profile URL for every synchronized team using `organization_id`, `team_id`, and `cloud_id`.
- Ensure reruns do not duplicate or lose team profile links (upsert-safe behavior).
- Render team names as outbound links in Teams dashboard and Team Details, opening in a new tab.
- Add subtle external-link affordance in the team title area while preserving existing design language.

**Non-Goals:**
- Reworking team search/filter logic or navigation architecture.
- Introducing new backend endpoints or replacing existing team payload contracts.
- Implementing role-based permission checks for outbound navigation.

## Decisions

1. **Canonical link source and fallback behavior**
- Decision: Prefer upstream `profileUrl` when present; otherwise synthesize `team_profile_url` as `https://home.atlassian.com/o/{organization_id}/people/team/{team_id}?cloudId={cloud_id}` when all required IDs are available.
- Rationale: Preserves authoritative API links when available while guaranteeing stable link availability for current tenants.
- Alternative considered: Only use upstream URL and leave null otherwise. Rejected because UX would be inconsistent across teams.

2. **Database schema extension in `teams` table**
- Decision: Add a dedicated `team_profile_url` text column in `teams` and include it in upsert update set.
- Rationale: Explicit column keeps contract clear and query-friendly versus extracting from JSON blobs.
- Alternative considered: Store only inside `team_json`. Rejected due to higher frontend coupling and less reliable SQL projection.

3. **Frontend rendering contract**
- Decision: Use `team_profile_url` from backend responses and render anchor tags with `target="_blank"` and `rel="noopener noreferrer"`.
- Rationale: Meets navigation requirement while mitigating tab-nabbing risks.
- Alternative considered: In-app route proxy/redirect. Rejected as unnecessary complexity for external destination.

4. **Visual affordance**
- Decision: Add a subtle external-link icon beside team title/header and style links with theme-aligned color/hover/focus states.
- Rationale: Communicates external destination without disrupting layout hierarchy.
- Alternative considered: Icon-only action button. Rejected because requirement explicitly needs team name to be actionable.

## Risks / Trade-offs

- **[Risk] Missing `organization_id` in some payloads may prevent deterministic link synthesis** -> **Mitigation:** Persist null/empty link when synthesis inputs are absent, preserve any upstream `profileUrl`, and avoid broken URLs.
- **[Risk] Existing DB files may lack the new column** -> **Mitigation:** Add migration-safe column creation (`ALTER TABLE` guard) in initialization path.
- **[Risk] UI regressions in compact/mobile layouts** -> **Mitigation:** Keep icon subtle, test team list/detail rendering at desktop/mobile breakpoints.
- **[Trade-off] Additional contract field increases frontend/backend coupling slightly** -> **Mitigation:** Keep field additive and backward-compatible.

## Migration Plan

1. Add/verify `team_profile_url` column creation in DB initialization and migration helpers.
2. Update team sync save path to write and upsert canonical profile link.
3. Ensure response/read models expose `team_profile_url` to frontend consumers.
4. Update Teams and Team Details rendering to link team names to external profile URL in new tabs.
5. Add CSS for link presentation and external icon affordance.
6. Validate via unit tests for persistence and UI smoke checks.

Rollback strategy:
- Revert frontend link rendering to plain text if issues are found.
- Keep additive DB column in place (safe no-op); backend can stop writing to it without data loss.

## Open Questions

- Should teams without resolvable profile URL render as plain text or disabled link style with tooltip?
- Should the external icon appear in both list rows and detail header, or detail header only?
