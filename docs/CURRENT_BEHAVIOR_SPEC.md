# Central Dashboard Current Behavior Specification

## 1. Scope and Source of Truth

This specification describes currently implemented behavior as observed in code and tests, not planned behavior.

Primary implementation sources:
- main.py
- database.py
- services.py
- scraper.py
- frontend/app.js

Primary validation sources:
- tests/test_main_team_defaults.py
- tests/test_metrics_status_rules.py
- tests/test_ticket_team_mapping.py
- tests/test_scraper_fallback.py
- tests/test_frontend_team_links.py

## 2. Runtime Architecture

### 2.1 Backend runtime
- FastAPI application serves frontend and JSON API endpoints.
- SQLite is used as the local cache and analytics store.
- Optional APScheduler background job executes periodic sync.
- Sync execution is thread-based with shared in-memory state and lock coordination.

### 2.2 Data flow summary
1. Runtime inputs provide one or more Jira board links.
2. Service layer validates each link and discovers ticket keys.
3. Service layer fetches ticket details and derives dependency metadata.
4. Database layer persists current tickets, dependencies, run history, and unresolved link events.
5. API layer serves filtered ticket rows, metrics, teams workspace, and InfoComm schedule data.
6. Frontend loads sync status, metrics, tickets, and teams, then renders tab-specific views.

### 2.3 Team metadata source model
- Team source of truth is `inputs/team_details.json`.
- `members[]` drives team roster and assignee-to-team fallback mapping.
- `components[]` is used as component-to-team alias input for ticket team resolution.

## 3. API Behavior (Implemented)

### 3.1 GET /
- Returns frontend/index.html.
- Returns 404 if frontend index file is missing.

### 3.2 GET /api/sync/status
- Returns two sections:
  - runtime: in-memory sync status (running flag, trigger, start time, queued manual request, last error).
  - persisted: latest sync run summary from SQLite and total cached ticket count.

### 3.3 POST /api/sync/manual
- Non-blocking trigger for sync worker thread.
- If sync already running:
  - manual trigger is accepted and queued for immediate next run.
  - scheduled trigger is rejected/skipped.

### 3.4 GET /api/tickets
Supported filters:
- status (repeatable, CSV supported)
- assignee (repeatable)
- team (repeatable)
- status_exclude (repeatable, CSV supported)
- assignee_exclude (repeatable)
- search (LIKE match on ticket_key and summary)
- board_id (substring match in source_links_json)
- limit (optional)
- offset (default 0)

Response includes:
- total, limit, offset
- items (ticket rows with resolved team metadata and parsed dependencies)
- filter_options (statuses, assignees, teams)
- groups (team/member grouped hierarchy)

Important default behavior:
- If team filter is not explicitly provided, ticket and metric endpoints default to current team dropdown options from filter metadata.

### 3.5 GET /api/metrics
- Uses same filter semantics as /api/tickets.
- Returns:
  - kpis.total_active_tickets
  - kpis.open_bug_count
  - kpis.stale_tickets_over_14_days
  - active_by_status
  - dependency_summary (blockers, inter_team, intra_team)

Active ticket rule:
- Excludes done and rejected.
- Excludes statuses equal to or ending with todo after whitespace normalization.
- Includes empty/null statuses as active.

### 3.6 GET /api/teams
- Returns teams workspace data from roster + filtered ticket metrics.
- Does not apply dropdown-team defaults when no explicit team filter is supplied.
- Team visibility is controlled by dashboard.team_visibility_keywords.

### 3.7 GET /api/teams/{team_id}
- Returns team detail panels:
  - team metadata and members
  - tickets_assigned with metrics
  - work_done subset
  - tickets_reported based on reporter-to-member matching
  - timeline buckets (todo, in_progress, done)

### 3.8 GET /api/infocomm/schedule/{show}
- Allowed show values: india, global.
- Optional refresh=true forces scrape.
- Always returns dates-only payload shape: list of { date }.
- On scrape failure:
  - if cache exists, returns cached data normalized to dates-only.
  - if no cache exists, returns HTTP 500.

### 3.9 GET /api/releases
- Optional project_key query parameter is accepted and forwarded to existing service logic.
- Response is proxied from the existing services.fetch_release_details integration.
- Response includes fetched_at, project_key, releases list, and may include error when upstream Jira release retrieval fails.

### 3.10 Not exposed as route
- `database.build_network_graph` exists in the data layer.
- No `/api/network` route is currently exposed by `main.py`.

## 4. Service Layer Behavior

### 4.1 Jira input validation
Each board link is validated for:
- scheme: must be http or https
- host: must match configured Atlassian host or allowed aliases
- URL pattern: must match supported board URL shapes

Invalid links are recorded in unresolved_links and partial_errors.

### 4.2 Ticket discovery strategy
For each valid board:
1. Build discovery JQL from configured filter or project key inferred from URL.
2. Prefer Jira Search API path(s) with endpoint fallback order.
3. If search fails, fall back to Agile board issue discovery.

### 4.3 Ticket detail fetch
- Details are fetched concurrently with bounded worker count.
- Optional cap ATLASSIAN_MAX_TICKET_FETCH_COUNT can truncate large boards.
- Truncation and per-ticket failures are captured as partial_errors.

### 4.4 Dependency parsing and aggregation
- Each ticket issuelinks list is normalized into:
  - blockers
  - blocking
  - other_dependencies
- Cross-project comparison labels each relation as intra_team or inter_team.
- Top-level dependency_analysis summarizes totals and detailed edge lists.

### 4.5 TLS warning suppression guardrails
- Suppression policy is configurable but blocked by default in production-like modes unless explicit override is set.
- Runtime policy status is reported and warning suppression is conditionally applied.

## 5. Persistence and Data Model Behavior

### 5.1 Core tables
- sync_runs
- tickets_current
- ticket_dependencies_current
- ticket_history_log
- unresolved_link_events
- sync_runtime_state

### 5.2 Schema evolution
- init_db performs additive schema upgrades for missing team columns.
- Team fields support both primary team and multi-team membership JSON arrays.

### 5.3 Upsert and history behavior
- persist_extraction_result writes one sync run row per invocation.
- Existing dependency rows are replaced each run.
- Ticket rows are upserted by ticket_key.
- Field-level change history is recorded for tracked fields.

### 5.4 Team assignment resolution
Priority order:
1. Resolve from components (supports exact, canonical, substring, and alias mapping).
2. Fallback to assignee primary team from team roster.
3. If unresolved, ticket remains unmapped.

Multi-team behavior:
- team_ids_json and team_names_json store all resolved team matches.
- Primary team fields keep first resolved team for backward compatibility.

## 6. Frontend Behavior Contract

### 6.1 Data loading pattern
- Startup loads sync status then dashboard data.
- Dashboard data fetches in parallel:
  - /api/metrics (with shared filters)
  - /api/tickets (with shared filters)
  - /api/teams (without shared filters)
- A global loading indicator tracks frontend API requests except sync status polling.

### 6.2 Tab behavior
- Teams, InfoComm, and Release tabs hide the main filter controls.
- Teams tab supports local text search over team cards.
- Team details panel renders plain text title and member table.
- InfoComm tab renders dates-only cards and empty-state message when no dates are available.
- InfoComm show selector currently exposes India and Global.
- Release tab renders a releases table with columns: Release Name, Release Date, and Status.
- Release tab displays explicit loading, empty, and error states and loads data from /api/releases on first activation.
- Release tab includes client-side Release Name and Status filters for table rows, with a clear-filters action.
- Release table includes a left-most multi-row checkbox selection column for batch dependency operations.
- Release tab includes relationship controls for Depends On and Released Together with searchable multi-select inputs and an Apply action.
- Release dependency relationships persist in a local JSON document keyed by Jira release id with depends_on and co_releases arrays.
- Released Together relationships are maintained bidirectionally in persisted relationship data.
- Release relationship persistence includes silent stale-id scrubbing against current Jira release ids before render and save.
- Release tab includes a graph panel toggle that opens a dependency graph view.
- Graph view includes a multi-select status filter for Released, Planned, Archived, and Overdue.
- Graph omits orphan releases with zero depends_on and zero co_releases relationships.
- Graph visually clusters co-release groups and applies status color mapping (Released green, Planned light blue, Archived dark orange, Overdue bright red).
- Release table headers are clickable and use tri-state sorting per column: ascending, descending, then unsorted default.
- Switching to a different release column starts sorting in ascending mode for the new column.
- Release Date sorting is date-aware and chronological (oldest-to-newest for ascending, newest-to-oldest for descending).
- Active release sort header shows a direction indicator, and unsorted mode clears active indicators.

### 6.3 Filter behavior
- Status supports CSV query compatibility.
- Multi-select controls use click-to-toggle behavior.
- Double-click on status/assignee marks exclusion.
- URL query key for board in browser state is board, while API uses board_id.

## 7. Edge Cases and Failure Semantics

### 7.1 Sync lifecycle and concurrency
- Startup sync can be skipped if a recent run completed within cooldown window.
- Manual request during active run is queued exactly once via manual_requested flag.
- Scheduled request during active run is skipped.

### 7.2 Team filtering edge behavior
- Team filter is case-insensitive and whitespace-tolerant.
- Filtering supports both team_id/team_name and multi-team JSON memberships.
- Legacy rows lacking team metadata are matched by assignee-to-roster fallback.
- Unmapped Team option targets tickets with no resolvable team assignment.

### 7.3 Filter options behavior
- Team dropdown options are derived from stored tickets but constrained by team_dropdown_keywords.
- Team dropdown keyword filtering is independent from team_visibility_keywords.
- Team dropdown options ignore currently selected team filters to prevent option disappearance.

### 7.4 Scraper resilience
- Scraper errors return fallback data from JSON or CSV when available.
- If scraping fails and fallback file is missing/unreadable, empty list is returned by scraper module.
- API wrapper may convert this into HTTP 500 when no cache is available.

### 7.5 Endpoint inconsistencies
- database.py provides build_network_graph, but main.py does not expose /api/network in the current implementation.
- docs/API_CONTRACT_SHEET.md includes /api/network, which is currently out of sync with active routes.

## 8. Validation Criteria

### 8.1 Automated validation currently present

A. Team default behavior validation
- /api/tickets and /api/metrics default to dropdown team options when team filter omitted.
- /api/teams does not use dropdown defaults.

B. Metrics status-rule validation
- done, rejected, todo variants are excluded from active KPI.
- in-progress and empty statuses are included.

C. Team mapping and filtering validation
- Team resolution from roster, component aliases, assignee fallback, and multi-team JSON fields.
- Team filters support case/whitespace tolerance.
- Unmapped behavior works for inclusion-only and selection-only flows.
- Dropdown and visibility keyword behavior is independently validated.

D. Scraper fallback validation
- Failure without fallback returns empty list.
- Failure with JSON/CSV fallback returns previous persisted data.

E. Frontend contract validation
- Team detail title is plain text.
- Team, InfoComm, and Release tabs hide filter controls and teams call uses /api/teams base route.
- InfoComm panel uses dates-only rendering.
- Release panel uses /api/releases and renders table/empty/error states.
- Release panel supports Release Name and Status row filtering with clear action.
- Release panel supports selection-based dependency editing and local relationship JSON persistence keyed by release id.
- Release graph panel supports status-based visibility filtering, co-release clustering, and orphan-node omission.
- Release table supports tri-state sortable headers with active direction indicators.
- Release Date column sorting is chronological via date-aware comparison.

### 8.2 Recommended manual validation checklist

1. Sync and scheduling
- Start app with scheduler enabled and verify startup cooldown skip behavior.
- Trigger manual sync during active scheduled run and confirm queued follow-up run.

2. Team filtering and options
- Verify selecting all team dropdown options includes unmapped tickets when offered.
- Verify selecting only Unmapped Team excludes mapped rows.
- Verify visibility keywords restrict Teams workspace independently of dropdown keywords.

3. API failure paths
- Use invalid show value for /api/infocomm/schedule/{show} and confirm HTTP 400.
- Force scraper failure with no cache and confirm HTTP 500 from API.
- Provide invalid Jira board links and confirm unresolved_links plus partial_errors.

4. Data integrity
- Run sync twice with ticket status changes and verify ticket_history_log diffs.
- Verify dependency counts align with ticket_dependencies_current rows for filtered scopes.

5. Frontend behavior
- Confirm filters are hidden on Teams, InfoComm, and Release tabs.
- Confirm board query persistence uses board in URL while API receives board_id.

## 9. Non-Goals and Out-of-Scope

- This document does not define future target-state architecture.
- This document does not prescribe UX redesigns or new API contracts.
- This document does not include deployment/security hardening beyond currently coded behavior.

## 10. Change Control

When implementation changes, update this file and ensure test coverage is added or adjusted for:
- endpoint shape changes
- filtering semantics
- team resolution logic
- scheduler/sync concurrency behavior
- scraper fallback semantics
