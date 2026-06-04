## Why

The dashboard currently centers on tickets, metrics, and dependency networks, but it does not provide a team-first workflow for reviewing delivery ownership, reported work, and progress by Jira team roster. A dedicated Teams experience and team-aware filtering are needed now to convert the existing cached team and ticket datasets into actionable operational views without introducing direct live-query coupling.

## What Changes

- Add a new Teams navigation destination in the side navigation and route to a dedicated Teams view/template.
- Introduce a Teams main view that lists valid teams with member rosters and external Jira profile links that open in a new tab with an external-link affordance.
- Add a team detail workspace with four tabs: Tickets Assigned, Work Done, Tickets Reported, and Timeline.
- Add a multi-select Team filter to global filters and cascade the Assignee filter to selected team rosters, including select-all and clear-all roster shortcuts.
- Update Tickets rendering to strict hierarchical grouping: Team accordion groups with inline metrics, then nested assignee groups within each team.
- Extend backend query paths in database.py to support efficient team-member-ticket joins for team filters, grouped ticket views, and team tab metrics without N+1 patterns.
- Add loading skeleton states for team timelines and graph/timeline-dependent panes to keep UX stable during data fetch from cache.

## Capabilities

### New Capabilities
- `team-centric-dashboard-workspace`: Introduces Teams navigation, team roster/detail tabs, roster-linked profile actions, and timeline visualization behavior.
- `team-aware-ticket-filtering-and-grouping`: Introduces cascading multi-select Team filtering, assignee cascade logic, and two-tier Team -> Member ticket grouping.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extends existing dashboard filter and tab interaction requirements to include Teams route integration, additional skeleton states, and visual differentiation between Reported vs Assigned views.

## Impact

- Affected backend modules: database.py query helpers, new team-centric read methods, and API route handlers in main.py that delegate only through database.py.
- Affected frontend modules: frontend/app.js state, routing, filter orchestration, rendering logic, and frontend/index.html template sections for Teams view and tabbed panels.
- Data dependencies: teams/team_members tables in dashboard_cache.db and cached extraction payload compatibility with outputs/jira_teams_and_members_response.json and outputs/kanban_ticket_details_response.json.
- Performance and correctness: requires relational JOIN-based queries and pre-aggregated counts per team/member context to avoid repeated per-team queries.
