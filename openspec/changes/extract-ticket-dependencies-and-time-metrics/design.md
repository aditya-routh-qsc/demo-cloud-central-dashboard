## Context

The current Kanban extraction service fetches active issues and standard attributes, but it lacks native visibility into blocker directionality, dependency ownership across teams, and deeper time-tracking attributes. It also depends on on-demand Jira API calls, which introduces latency and rate-limit risk.

This change introduces dependency and time-metric extraction, plus persistent scheduled caching in SQLite so frontend calls serve fast local data while preserving historical sync updates and live sync status.

## Goals / Non-Goals

**Goals:**
- Extract both inward and outward ticket dependencies.
- Correctly distinguish blockers from non-blocking relations.
- Classify dependencies by issue key prefix to flag cross-team dependencies.
- Extract reporter metadata and standard/custom time metrics for velocity/risk analysis.
- Persist data in SQLite on a periodic schedule.
- Serve frontend endpoints from cached DB records instead of live Jira calls.
- Support historical updates and real-time sync tracking in dashboard responses.
- Use one global snapshot model where tickets are unique and board membership is tracked via `source_links`.

**Non-Goals:**
- Complex normalized relational modeling beyond what is required for fast reads.
- Cloud backup/replication for SQLite in this scope.
- Project metadata fallback for team classification in this phase (issue key prefix is sufficient now).

## Decisions

- **1. Project-Prefix Partitioning**: Use issue key prefix (text before `-`, for example `QSYSCLOUD`) as team identity. Rationale: It is reliable for current org mappings.
- **2. Explicit Blocker Classification**: Treat link types containing blocked/blocker or standard `Blocks` semantics as blockers. Rationale: avoids misclassifying informational links.
- **3. Story Points Fallback**: Read story points from `customfield_10006`, then `customfield_10016` fallback. Rationale: Jira custom field variance.
- **4. SQLite + Scheduler**: Use local SQLite with periodic scheduler (default 60 minutes from `.config`, configurable). Rationale: zero-config, reliable local cache.
- **5. Manual Sync Priority**: If manual and scheduled sync overlap, manual sync takes priority and scheduled run is deferred/skipped. Rationale: user-triggered freshness intent should win.
- **6. Fire-and-Forget Manual Sync**: Manual sync APIs return immediately with run status tracking (`syncing`, `last_synced_at`, `last_error`). Rationale: large syncs can take time and should not block clients.
- **7. Global Upsert Snapshot**: Maintain one global ticket store keyed by unique ticket key, upserting records and merging `source_links` membership. Rationale: dedup across boards with traceable board ownership.

## Risks / Trade-offs

- **Risk**: Data may be stale between syncs.
  **Mitigation**: Configurable interval (default 60 min), plus manual sync action and visible sync status.
- **Risk**: SQLite has no remote backup in this scope.
  **Mitigation**: Keep DB in secured local path and document operational backup expectations externally.
- **Risk**: Large syncs can encounter rate limits/transient 502 errors.
  **Mitigation**: Retry/backoff boundaries, partial error tracking, and non-blocking manual sync UX.

## Migration Plan

- Extend `services.py` query field mapping to include dependencies and time metrics.
- Add dependency parsing and summary aggregation helpers.
- Add SQLite persistence schema for tickets, dependency summaries, and sync-run history.
- Add scheduler initialization in `main.py` with `.config`-driven interval defaulting to 60 minutes.
- Update API endpoints to read exclusively from SQLite cached state.
- Add manual sync endpoint that starts background sync and returns status immediately.
- Implement overlap policy: manual sync overrides scheduled sync.
- Validate dedup upsert behavior for tickets shared across boards.

## Open Questions

- Should scheduled syncs be queued after manual sync completion or skipped entirely when overlap occurs?
- What retention period should be used for sync-run history records?
- Should stale threshold for UI warning be equal to interval or interval + grace window?
