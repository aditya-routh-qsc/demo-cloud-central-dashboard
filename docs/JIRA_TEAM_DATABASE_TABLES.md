# Dashboard Database Tables

This document describes all application tables currently used by the dashboard.

Core ticket-sync tables are created in [database.py](../database.py).
Jira team-sync tables are created and migrated in [services.py](../services.py).

## sync_runs

Purpose: Stores one row per sync execution (manual or scheduled).

Columns:
- run_id (TEXT, PK): Sync run identifier (UUID).
- trigger_type (TEXT): Trigger source, usually manual or scheduled.
- started_at (TEXT): UTC ISO timestamp when run started.
- completed_at (TEXT): UTC ISO timestamp when run completed.
- status (TEXT): Run status, such as success or partial.
- links_provided (INTEGER): Number of input board links.
- links_processed (INTEGER): Number of successfully processed links.
- tickets_discovered (INTEGER): Number of ticket keys discovered.
- tickets_resolved (INTEGER): Number of ticket details resolved and persisted.
- unresolved_links (INTEGER): Number of links that failed validation/discovery.
- errors (INTEGER): Number of partial errors reported.
- error_summary (TEXT): Compact summary of errors.

## tickets_current

Purpose: Current snapshot of normalized Jira ticket fields used by the dashboard.

Columns:
- ticket_key (TEXT, PK): Jira issue key.
- project_key (TEXT): Derived Jira project key.
- summary (TEXT): Issue summary.
- issue_type (TEXT): Jira issue type.
- status (TEXT): Current status.
- priority (TEXT): Priority label.
- assignee (TEXT): Assignee display name.
- reporter (TEXT): Reporter display name.
- report_date (TEXT): Created timestamp.
- due_date (TEXT): Due date.
- resolution_date (TEXT): Resolution date/time.
- updated (TEXT): Last updated timestamp from Jira.
- story_points (REAL): Story points field value.
- time_original_estimate (INTEGER): Original estimate in seconds.
- time_estimate (INTEGER): Remaining estimate in seconds.
- time_spent (INTEGER): Time spent in seconds.
- source_links_json (TEXT): JSON array of source board links.
- dependencies_json (TEXT): JSON object with parsed dependency groups.
- last_seen_run_id (TEXT): Latest sync run_id that observed this ticket.
- updated_at (TEXT): UTC ISO timestamp of local row update.

## ticket_dependencies_current

Purpose: Current ticket dependency edges for network/metrics views.

Columns:
- source_ticket_key (TEXT): Source ticket key.
- target_ticket_key (TEXT): Target ticket key.
- dependency_type (TEXT): blockers, blocking, or other_dependencies.
- relation_name (TEXT): Jira relation type name.
- relation_description (TEXT): Jira relation description.
- direction (TEXT): inward or outward.
- classification (TEXT): intra_team or inter_team.
- source_project_key (TEXT): Source project key.
- target_project_key (TEXT): Target project key.
- target_status (TEXT): Cached target ticket status.
- last_seen_run_id (TEXT): Latest sync run_id that observed this edge.

Primary key:
- (source_ticket_key, target_ticket_key, dependency_type, relation_name, direction)

## ticket_history_log

Purpose: Append-only change log for selected tracked ticket fields across sync runs.

Columns:
- id (INTEGER, PK AUTOINCREMENT): History row id.
- ticket_key (TEXT): Ticket key.
- run_id (TEXT): Sync run identifier.
- changed_at (TEXT): UTC ISO timestamp of change detection.
- field_name (TEXT): Field that changed.
- old_value (TEXT): Previous value.
- new_value (TEXT): New value.

## unresolved_link_events

Purpose: Captures unresolved board link events for diagnostics.

Columns:
- id (INTEGER, PK AUTOINCREMENT): Event row id.
- run_id (TEXT): Sync run identifier.
- board_link (TEXT): Input link that failed.
- board_id (TEXT): Parsed board id when available.
- reason (TEXT): Failure reason.
- created_at (TEXT): UTC ISO timestamp.

## sync_runtime_state

Purpose: Generic key-value state store for sync runtime metadata.

Columns:
- state_key (TEXT, PK): State key.
- state_value (TEXT): State value.

## teams

Purpose: Stores one row per Jira team with normalized fields plus raw payload.

Columns:
- team_id (TEXT, PK): Jira team identifier (teamId or id).
- display_name (TEXT): Team display name.
- description (TEXT): Team description.
- cloud_id (TEXT): Jira cloud/site id used for team sync.
- organization_id (TEXT): Organization id when available.
- state (TEXT): Team state.
- team_type (TEXT): Team type.
- is_verified (INTEGER): Boolean flag represented as 1/0.
- profile_url (TEXT): Team profile URL when available.
- member_count (INTEGER): Team member count when available.
- includes_you (INTEGER): Whether requester is team member (1/0).
- team_json (TEXT): Full raw team payload JSON.
- updated_at (TEXT): UTC ISO timestamp of local row update.

Upsert key:
- ON CONFLICT(team_id) DO UPDATE

## team_members

Purpose: Stores one row per (team_id, account_id) with normalized and raw member data.

Columns:
- id (INTEGER, PK AUTOINCREMENT): Surrogate row id.
- team_id (TEXT): Parent team id.
- account_id (TEXT): Atlassian account id.
- display_name (TEXT): Member display name.
- email (TEXT): Member email when available.
- canonical_account_id (TEXT): Canonical account id when available.
- account_status (TEXT): Account status when available.
- nickname (TEXT): Nickname when available.
- picture (TEXT): Profile picture URL when available.
- zoneinfo (TEXT): Timezone info.
- locale (TEXT): Locale info.
- org_id (TEXT): Organization id when available.
- profile_url (TEXT): Jira profile URL (https://<domain>/jira/people/<account_id>).
- member_role (TEXT): Team role when available.
- member_state (TEXT): Team membership state when available.
- member_json (TEXT): Full raw member payload JSON.
- updated_at (TEXT): UTC ISO timestamp of local row update.

Unique key and upsert behavior:
- UNIQUE(team_id, account_id)
- ON CONFLICT(team_id, account_id) DO UPDATE

## sqlite_sequence (SQLite internal)

Purpose: Internal SQLite table used to track AUTOINCREMENT values for tables such as ticket_history_log, unresolved_link_events, and team_members.

Notes:
- This is system-managed and should not be edited by application code.
