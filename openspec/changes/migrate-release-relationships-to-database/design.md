## Context

The current release relationship workflow stores dependency and co-release mappings in frontend-local JSON, while the release source-of-truth comes from Jira payloads retrieved through backend services. This split weakens integrity guarantees, makes concurrent or repeated updates error-prone, and leaves stale mappings when Jira releases are removed or renamed.

The target state is a backend-owned SQLite persistence model in database.db with all SQL logic centralized in database.py. API handlers and services must call procedural database.py functions rather than embedding SQL directly.

Constraints:
- Existing release identifiers from Jira remain the canonical keys for relationship mapping.
- Persistence must support both dependency edges and co-release symmetry.
- Re-applying relationship edits must be idempotent.
- Reconciliation must remove relationships referencing release IDs not present in active Jira payloads.

## Goals / Non-Goals

**Goals:**
- Define and initialize a normalized SQLite schema for release relationship graph edges.
- Expose clean database.py functions for initialization, retrieval, persistence, and reconciliation.
- Enforce bidirectional co-release integrity in storage operations.
- Provide retrieval utilities that return frontend-friendly maps filtered by active release IDs.
- Ensure stale relationship cleanup based on current Jira release ID sets.
- Remove deprecated backend JSON persistence code paths.

**Non-Goals:**
- Changing Jira release fetch behavior or release identity semantics in services.py.
- Redesigning frontend interaction flow or graph rendering logic.
- Introducing external databases or networked persistence.
- Building generic ORM abstractions; this remains SQLite + procedural helpers.

## Decisions

### 1) Use dedicated edge tables with composite uniqueness
Decision:
- Create `release_dependencies(release_id, depends_on_id)` and `release_co_releases(release_id, co_release_id)` tables in SQLite.
- Add composite primary keys or unique indexes on each edge pair to prevent duplicates.

Rationale:
- Join tables model graph edges naturally and support set-based reconciliation.
- Composite uniqueness provides idempotency for repeated apply operations.

Alternatives considered:
- Single JSON blob column: rejected due to poor queryability and harder reconciliation.
- One unified relationship table with a type column: rejected for reduced readability and higher accidental-mix risk.

### 2) Centralize all SQL in database.py with transaction-scoped write operations
Decision:
- Implement all schema, CRUD, and cleanup queries as dedicated functions in database.py.
- Wrap apply/reconcile flows in explicit transaction boundaries.

Rationale:
- Meets decoupling constraints and keeps API handlers thin.
- Transactions protect integrity across multi-row rewrites.

Alternatives considered:
- SQL in route handlers: rejected by architecture constraint.
- Lightweight ORM migration: rejected as unnecessary complexity for current scope.

### 3) Persist co-releases as explicit symmetric directed pairs
Decision:
- For each co-release pair (A, B), ensure both (A, B) and (B, A) rows exist.
- During save, normalize and enforce symmetry before commit.

Rationale:
- Simplifies retrieval for frontend consumers and avoids ambiguity about direction.
- Keeps behavior deterministic when users submit partial mappings.

Alternatives considered:
- Canonical ordered storage only once (min, max): rejected because retrieval then needs directional expansion on every read.

### 4) Rewrite-target rows on apply for selected releases
Decision:
- Apply operation replaces relationship rows for selected release IDs: delete previous edges for selected IDs, then insert normalized new rows.

Rationale:
- Idempotent and predictable state transitions.
- Prevents residual rows from earlier edits.

Alternatives considered:
- Incremental diff updates: rejected for higher complexity and error surface.

### 5) Reconcile against active Jira IDs with set-based deletion
Decision:
- Add scrub function that removes any row where either endpoint is not in the active ID set.

Rationale:
- Maintains graph integrity when Jira releases disappear or are renamed.
- Keeps local database aligned with live source data.

Alternatives considered:
- Soft-delete rows: rejected because consumers need clean active graph semantics.

## Risks / Trade-offs

- [Risk] Large active ID sets may create expensive IN clauses in scrub queries. -> Mitigation: chunk IDs for parameterized SQL and run within transaction.
- [Risk] Symmetry enforcement could insert redundant pairs repeatedly. -> Mitigation: use INSERT OR IGNORE with composite uniqueness.
- [Risk] Partial failure during apply could leave inconsistent edges. -> Mitigation: transaction rollback on exceptions.
- [Risk] Existing JSON-based logic may continue to be called accidentally. -> Mitigation: remove deprecated paths and add integration tests covering database-backed endpoints.
- [Trade-off] Explicit symmetric storage increases row count for co-releases. -> Accepted for simpler retrieval and deterministic API behavior.

## Reference DDL (database.db)

```sql
CREATE TABLE IF NOT EXISTS release_dependencies (
	release_id TEXT NOT NULL,
	depends_on_id TEXT NOT NULL,
	created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (release_id, depends_on_id),
	CHECK (release_id <> depends_on_id)
);

CREATE TABLE IF NOT EXISTS release_co_releases (
	release_id TEXT NOT NULL,
	co_release_id TEXT NOT NULL,
	created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (release_id, co_release_id),
	CHECK (release_id <> co_release_id)
);

CREATE INDEX IF NOT EXISTS idx_release_dependencies_release_id
	ON release_dependencies (release_id);

CREATE INDEX IF NOT EXISTS idx_release_dependencies_depends_on_id
	ON release_dependencies (depends_on_id);

CREATE INDEX IF NOT EXISTS idx_release_co_releases_release_id
	ON release_co_releases (release_id);

CREATE INDEX IF NOT EXISTS idx_release_co_releases_co_release_id
	ON release_co_releases (co_release_id);
```

## database.py Interface (Signatures + Docstrings)

```python
def init_release_relationship_schema(db_path: str = "database.db") -> None:
		"""Create or migrate release relationship tables and indexes idempotently."""


def get_release_relationship_maps(
		active_release_ids: list[str],
		db_path: str = "database.db",
) -> dict[str, dict[str, list[str]]]:
		"""Return frontend-ready dependency/co-release maps filtered to active IDs only.

		Response shape:
			{
				"dependencies": {"<release_id>": ["<depends_on_id>", ...]},
				"co_releases": {"<release_id>": ["<co_release_id>", ...]}
			}
		"""


def save_release_relationship_updates(
		selected_release_ids: list[str],
		depends_on_ids: list[str],
		co_release_ids: list[str],
		db_path: str = "database.db",
) -> dict[str, int]:
		"""Rewrite relationships for selected releases transactionally and idempotently.

		Guarantees symmetric co-release storage so (A, B) implies (B, A).
		Returns write metrics such as deleted_rows and inserted_rows.
		"""


def reconcile_release_relationships(
		active_release_ids: list[str],
		db_path: str = "database.db",
) -> dict[str, int]:
		"""Delete stale dependency/co-release edges that reference inactive Jira release IDs.

		Returns cleanup metrics for each table.
		"""


def normalize_relationship_payload(
		selected_release_ids: list[str],
		depends_on_ids: list[str],
		co_release_ids: list[str],
		active_release_ids: list[str],
) -> tuple[list[str], list[tuple[str, str]], list[tuple[str, str]]]:
		"""Normalize IDs, drop self-links, deduplicate edges, and prepare DB-ready tuples."""
```

## Integration Plan (API + Jira Stream)

1. On startup (or first release request), call `init_release_relationship_schema()`.
2. In release relationship read flows:
	 - Fetch active Jira releases from services.py.
	 - Build active ID set.
	 - Call `reconcile_release_relationships(active_ids)` to scrub stale edges.
	 - Call `get_release_relationship_maps(active_ids)` and return payload to frontend.
3. In release relationship apply flows:
	 - Validate request payload IDs against current active Jira IDs.
	 - Call `save_release_relationship_updates(...)`.
	 - Optionally call `get_release_relationship_maps(active_ids)` to return updated view model.
4. Remove deprecated JSON storage pathways and related fallback code once DB path is live.
5. Keep all route handlers SQL-free; database.py is the only SQL execution layer.
