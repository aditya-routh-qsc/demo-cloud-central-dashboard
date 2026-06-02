# Tasks - Extract Ticket Dependencies, Time Metrics, and Database Caching

- [x] Update `_process_jira_query` to extract and return `issuelinks`, `reporter`, `created`, `duedate`, `resolutiondate`, `timeoriginalestimate`, `timeestimate`, `timespent`, `customfield_10006`, and `customfield_10016`.
- [x] Add helper functions `parse_issue_dependencies` and `find_and_analyze_dependencies` in `services.py`.
- [x] Update `get_ticket_details_from_kanban_links` to request advanced metric fields and incorporate dependency parsing results.
- [x] Update CLI block (`if __name__ == "__main__":`) in `services.py` to emit dependency/time-metric summary output.
- [x] Create SQLite database connector and schema for tickets (global unique key), dependency data, sync status, and sync history.
- [x] Implement upsert policy on ticket key and merge/update `source_links` for multi-board membership.
- [x] Add `.config` support for configurable sync interval with default value of 60 minutes.
- [x] Set up background scheduler in `main.py` for periodic sync and enforce overlap rule: manual sync has priority over scheduled sync.
- [x] Implement fire-and-forget manual sync endpoint and sync-status endpoint(s) for UI indicators.
- [x] Update backend REST API endpoints in `main.py` (`/api/tickets`, `/api/metrics`, `/api/network`) to serve from SQLite only.
- [x] Verify DB read/write cycles, historical sync retention behavior, overlap handling, and scheduler execution.
