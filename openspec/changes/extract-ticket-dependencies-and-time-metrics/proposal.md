## Why

Jira Kanban boards have complex blockers and cross-team dependencies that are not visible in flat lists or standard Confluence reports. In addition, assessing ticket health and timeline risks requires key time metrics (story points, estimates, spent time) and reporter metadata. This change is needed to provide deep dependency graphing and rich time analytics directly from the Kanban extraction pipeline.

Querying the Jira API on every dashboard reload also causes significant latency and can trigger rate limits, so periodic database storage and caching are required for near-instant frontend loads. The dashboard must support both real-time status visibility and historical update tracking.

## What Changes

- **Query API Fields Expansion**: Extend requested fields to include `issuelinks`, `reporter`, `created`, `duedate`, `resolutiondate`, `timeoriginalestimate`, `timeestimate`, `timespent`, and story points (`customfield_10006`, `customfield_10016`).
- **Dependency Classifier**: Add `parse_issue_dependencies` to interpret Jira link direction and classify relationships into `blockers`, `blocking`, and `other_dependencies`, with `intra_team` and `inter_team` tags.
- **Dependency Aggregator**: Add `find_and_analyze_dependencies` to compute top-level dependency summaries, metrics, and explicit link pairs.
- **Periodic Database Storage**: Add SQLite persistence for raw ticket payloads, parsed dependencies, computed metrics, and sync history snapshots. Use scheduled background sync.
- **Sync Overlap Policy**: Prioritize manual sync over scheduled sync when overlap occurs, and keep manual sync fire-and-forget with status indicators.
- **Main.py Fetching Shift**: Move `main.py` endpoints (`/api/tickets`, `/api/metrics`, `/api/network`) to database reads only.
- **Multi-Board Dedup Upsert**: Enforce global unique ticket keys with upsert semantics (update if exists, insert if new) and keep `source_links` arrays updated so one ticket can belong to multiple boards.
- **Configurable Freshness SLA**: Add `.config`-driven sync interval with default set to 60 minutes.

## Capabilities

### New Capabilities

- `jira-dependency-analysis`: Parses and structures directional blocker chains and team-boundary dependency lines across Kanban issues.
- `jira-time-metrics-extraction`: Extracts created/due/resolution dates, reporter metadata, story points, and time-tracking values.
- `periodic-database-caching`: Periodically extracts and stores data locally to decouple UI reads from external API calls.
- `ticket-history-and-live-status`: Preserves historical sync updates while surfacing real-time sync status in APIs/UI.

### Modified Capabilities

- `extract-ticket-details-from-kanban-links`: Enhanced with dependency and time-metric enrichment and database-backed output.

## Impact

- **Affected code**: `services.py` (query/output enrichment and dependency parsing), `main.py` (database-backed API endpoints, scheduler setup, sync status APIs), database module(s) for SQLite persistence and history.
- **Affected output**: SQLite-backed cached dataset and historical sync records instead of transient JSON-only output.
- **Security impact**: SQLite files remain local within the user's secure directory; credentials remain in `.env`. No remote backup integration is introduced in this change.
- **Operational impact**: Dashboard reads become milliseconds-scale and avoid live Jira API calls during peak usage. Manual sync remains asynchronous with visible progress state.
