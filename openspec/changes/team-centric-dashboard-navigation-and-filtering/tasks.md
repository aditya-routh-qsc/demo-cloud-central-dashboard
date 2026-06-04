## 1. Data Query Foundations

- [x] 1.1 Add database.py helpers for team roster lookup and team-member identity mapping from teams and team_members tables.
- [x] 1.2 Implement JOIN-based ticket query helpers that correlate teams/team_members with tickets_current for assigned and reported views.
- [x] 1.3 Add grouped aggregation helpers for Team -> Member ticket hierarchies including total, in-progress, and blocked counts.
- [x] 1.4 Add timeline aggregation helper that maps ticket statuses into To Do, In Progress, and Done buckets per selected team.
- [x] 1.5 Add or verify supporting SQLite indexes for join/filter columns used by team and member correlation paths.

## 2. API and Controller Integration

- [x] 2.1 Add procedural API route handlers in main.py for Teams workspace data by delegating all SQL/data access to database.py.
- [x] 2.2 Extend existing filter parsing to accept multi-select team values and pass them into shared query builders.
- [x] 2.3 Implement assignee cascade contract endpoint/fields so assignee options shrink to selected team rosters.
- [x] 2.4 Expose payload shapes for team overview, team detail tabs, grouped ticket hierarchy, and timeline datasets.

## 3. Frontend Navigation and Teams Workspace

- [x] 3.1 Add Teams option in side navigation and route state handling for a dedicated Teams view template.
- [x] 3.2 Implement Teams main roster grid/list rendering with member profile links opening in new tabs and external-link icon treatment.
- [x] 3.3 Build team detail tab UI for Tickets Assigned, Work Done, Tickets Reported, and Timeline panels.
- [x] 3.4 Apply explicit visual distinction between Reported By and Assigned To contexts in team detail tabs.

## 4. Global Filters and Ticket Hierarchy Rendering

- [x] 4.1 Add multi-select Team control to global filters with state persistence and reset compatibility.
- [x] 4.2 Implement assignee cascading behavior with select-all and clear-all roster toggles for selected teams.
- [x] 4.3 Refactor Tickets tab rendering into Team accordion groups with nested member groups.
- [x] 4.4 Render team header badges with inline group metrics: total tickets, in-progress tickets, and blocked tickets.

## 5. Loading UX and Validation

- [x] 5.1 Add skeleton loading states for timeline and graph-adjacent panels during cache-backed request transitions.
- [x] 5.2 Verify no direct database access occurs outside database.py for new team features.
- [x] 5.3 Validate query performance and absence of N+1 patterns using representative cache sizes.
- [ ] 5.4 Run end-to-end manual checks for filter cascade, Teams tabs, grouping behavior, and Jira external link navigation.
