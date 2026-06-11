## 1. Schema and Initialization

- [x] 1.1 Add SQLite DDL in database.py for `release_dependencies(release_id, depends_on_id)` with composite uniqueness
- [x] 1.2 Add SQLite DDL in database.py for `release_co_releases(release_id, co_release_id)` with composite uniqueness
- [x] 1.3 Implement `init_release_relationship_schema(db_path: str = "database.db") -> None` to create tables/indexes idempotently

## 2. Database Interface Functions

- [x] 2.1 Implement connection helper(s) in database.py to centralize connection/cursor/transaction handling
- [x] 2.2 Implement retrieval function for active-filtered dependencies map (release_id -> list[depends_on_id])
- [x] 2.3 Implement retrieval function for active-filtered co-release map (release_id -> list[co_release_id])
- [x] 2.4 Implement consolidated retrieval helper returning frontend-ready relationship payload shape

## 3. Persistence and Symmetry Enforcement

- [x] 3.1 Implement save/apply function to rewrite relationship rows for selected release IDs in a transaction
- [x] 3.2 Normalize input IDs and deduplicate payload edges before writes
- [x] 3.3 Enforce bidirectional co-release storage so `(A,B)` guarantees `(B,A)`
- [x] 3.4 Ensure save operations are idempotent via delete+insert or conflict-safe insert patterns

## 4. Reconciliation and Scrubbing

- [x] 4.1 Implement scrub function accepting active Jira release IDs from services payload
- [x] 4.2 Delete stale dependency rows where either endpoint is absent from active IDs
- [x] 4.3 Delete stale co-release rows where either endpoint is absent from active IDs
- [x] 4.4 Return scrub metrics (rows removed per table) for logging/observability

## 5. Backend Integration and Cleanup

- [x] 5.1 Update release relationship API/service integration to call only database.py interface functions
- [x] 5.2 Remove deprecated JSON persistence pathways superseded by database.db storage
- [x] 5.3 Ensure route handlers do not contain inline SQL (database.py-only SQL policy)
- [x] 5.4 Add startup/initialization hook to ensure schema exists before first relationship operation

## 6. Validation and Regression Coverage

- [x] 6.1 Add unit tests for schema init and duplicate-insert idempotency behavior
- [x] 6.2 Add unit tests for co-release bidirectional enforcement on save
- [x] 6.3 Add unit tests for active-ID filtered retrieval behavior
- [x] 6.4 Add unit tests for stale-reference scrub behavior against simulated Jira ID changes
- [x] 6.5 Run targeted backend and frontend contract tests to verify no API regressions
