## Why

Release dependency and co-release mappings are currently persisted with a local JSON strategy, which is fragile for repeated updates, difficult to reconcile with live Jira churn, and not suitable for backend-centered data integrity guarantees. Moving persistence to SQLite now enables consistent, idempotent relationship updates and automated cleanup against the active Jira release set.

## What Changes

- Add database-backed persistence in database.db for release dependencies and co-release mappings using dedicated relationship tables.
- Add procedural database interface functions in database.py for schema initialization, upsert-style persistence, retrieval, filtering by active release IDs, and reconciliation cleanup.
- Add bidirectional enforcement for co-release edges so inserting (A, B) guarantees the inverse (B, A).
- Add reconciliation utilities that remove stale rows when release IDs no longer appear in live Jira release payloads.
- Update backend integration points to use database.py functions instead of frontend-local JSON persistence pathways.
- Remove deprecated backend/local JSON persistence code paths that duplicate release-relationship storage behavior.

## Capabilities

### New Capabilities
- `release-relationship-database-persistence`: Defines SQLite schema, CRUD behavior, bidirectional co-release integrity, active-ID filtering for retrieval, and automatic stale-reference reconciliation for release relationship graphs.

### Modified Capabilities
None.

## Impact

- Affected code: database.py, main.py route/service integration points, and release relationship backend wiring.
- Affected runtime artifact: database.db local SQLite file and schema lifecycle.
- APIs: Release relationship retrieval/apply endpoints continue to serve frontend graph consumers but source data from SQLite.
- Data integrity: Co-release symmetry and stale Jira ID cleanup become backend-enforced.
- Operational behavior: Re-applying relationship edits remains idempotent without duplicate-row or unique-constraint failures.
