## Context

The dashboard already serves ticket, metrics, and dependency-network views from cached SQLite data through database.py and FastAPI routes in main.py. The repository also stores synchronized Jira team/member data and ticket snapshots in dashboard_cache.db and emits equivalent JSON payloads in outputs/jira_teams_and_members_response.json and outputs/kanban_ticket_details_response.json.

The requested enhancement adds a team-centric workspace without violating current architectural constraints:
- Keep controller/query flow procedural.
- Keep all DB interactions in database.py.
- Avoid N+1 query patterns while correlating teams, members, assignees, and reporters.

## Goals / Non-Goals

**Goals:**
- Add Teams navigation and a dedicated Teams view with team roster display and member profile links.
- Add tabbed team detail panels: Tickets Assigned, Work Done, Tickets Reported, and Timeline.
- Add cascading multi-select Team filtering integrated with global filters and assignee cascade behavior.
- Restructure ticket grouping to Team -> Member hierarchy with accordion summaries.
- Implement JOIN-based, set-oriented queries in database.py for team metrics and grouped ticket retrieval.
- Add loading skeleton states for graph and timeline-heavy surfaces.

**Non-Goals:**
- No live Jira API calls from frontend routes.
- No replacement of existing sync ingestion architecture.
- No OOP service layer rewrite.
- No migration away from SQLite cache in this change.

## Decisions

1. Introduce team-aware API payloads backed by database.py-only query helpers
- Decision: Add new read helpers in database.py for team filter options, team roster mapping, grouped ticket payloads, team detail metrics, and timeline buckets.
- Rationale: Preserves current rule that data access is centralized in database.py and keeps route/controller code thin.
- Alternative considered: Build SQL directly in main.py per endpoint. Rejected due to architectural constraint and maintainability risk.

2. Correlate teams/members with tickets using relational JOINs and normalized comparison keys
- Decision: Use team_members display_name/account_id alongside tickets_current.assignee and tickets_current.reporter with case-normalized joins and optional alias handling.
- Rationale: tickets_current currently stores person-facing names while team_members has richer identity fields. Joining on normalized display name is required for immediate compatibility.
- Alternative considered: Full remap of ticket model to account_id-only ownership. Rejected for this change due to ingestion scope and migration risk.

3. Implement two-tier grouping server-side, render hierarchy client-side
- Decision: Backend returns a grouped payload keyed by team then member, with group-level counters precomputed.
- Rationale: Avoids repeated client-side aggregation and keeps metrics consistent across tabs.
- Alternative considered: Return flat rows and group in JS only. Rejected because it duplicates logic and increases risk of inconsistent totals.

4. Add Teams route and tab state to existing frontend state model
- Decision: Extend existing route/tab state in frontend/app.js to include Teams primary view and detail sub-tab selection.
- Rationale: Reuses existing navigation and fetch lifecycle patterns.
- Alternative considered: Introduce separate SPA router package. Rejected as unnecessary complexity.

5. Skeleton-first UX during async data resolution
- Decision: Add deterministic skeleton placeholders for team cards, ticket grouped rows, and timeline bars before content hydration.
- Rationale: Maintains perceived responsiveness and visual stability on cache reads.
- Alternative considered: Spinner-only loading. Rejected due to poor readability for dense layouts.

## Risks / Trade-offs

- [Identity mismatch between assignee/reporter names and team_members records] -> Mitigation: normalize casing/whitespace, include fallback matching, and expose unmapped buckets for diagnostics.
- [Expanded JOIN queries impact response times on large caches] -> Mitigation: add supporting indexes for team_id/account_id/display_name fields and use bounded aggregations.
- [Filter coupling could produce confusing assignee options] -> Mitigation: explicit cascade rules and select-all/clear-all roster controls with clear UI labels.
- [Timeline interpretation ambiguity across custom workflows] -> Mitigation: use configurable status-to-lane mapping with defaults (To Do/In Progress/Done) and expose unknown lane handling.

## Migration Plan

1. Add database.py query helpers and any required indexes in non-breaking migrations.
2. Add/extend API routes in main.py by delegating to new database.py helpers only.
3. Update frontend templates and app.js state/actions for Teams navigation, tabs, grouping, and skeletons.
4. Validate with existing cached database and output JSON references.
5. Rollback strategy: feature-flag Teams route and team filter; if disabled, existing tickets/metrics/network flows remain unchanged.

## Open Questions

- Should assignee mapping prefer account_id aliases when both display name and account identity are available?
- Should Tickets Reported include unresolved tickets only, or all statuses by default with status filters controlling scope?
- Are blocked counts in team accordion summary derived from dependency classification, status, or both?
