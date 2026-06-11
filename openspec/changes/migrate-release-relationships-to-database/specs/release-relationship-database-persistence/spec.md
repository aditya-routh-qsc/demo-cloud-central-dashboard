## ADDED Requirements

### Requirement: Relationship schema SHALL persist dependency edges
The system SHALL persist release dependency relationships in `database.db` using a dedicated table with one row per directed edge (`release_id`, `depends_on_id`) and uniqueness constraints that prevent duplicate edges.

#### Scenario: Schema initialization creates dependency table
- **WHEN** database schema initialization runs
- **THEN** the dependency table exists with `release_id` and `depends_on_id` columns and duplicate edge inserts are prevented by schema constraints

### Requirement: Relationship schema SHALL persist co-release edges with bidirectional integrity
The system SHALL persist co-release mappings in `database.db` using a dedicated table with one row per directed edge (`release_id`, `co_release_id`) and SHALL enforce symmetric storage so each submitted pair `(A, B)` has a matching `(B, A)` row.

#### Scenario: Save operation enforces co-release symmetry
- **WHEN** a save request includes co-release pair `(ID_A, ID_B)`
- **THEN** the database contains both `(ID_A, ID_B)` and `(ID_B, ID_A)` rows after commit

### Requirement: Save operations SHALL be idempotent and replace prior mappings for targeted releases
The system SHALL support re-application of relationship updates without duplicate-row errors by rewriting existing edges for targeted release IDs and inserting normalized relationship rows in a single transaction.

#### Scenario: Re-applying unchanged payload does not create duplicates
- **WHEN** the same relationship update payload is applied multiple times for the same selected release IDs
- **THEN** persistence succeeds each time and edge counts remain stable with no duplicate rows

### Requirement: Retrieval SHALL return active-release-filtered relationship maps
The system SHALL provide retrieval functions that return dependency and co-release maps filtered to an input set of active release IDs so consumers receive graph data only for currently relevant Jira releases.

#### Scenario: Retrieval omits inactive IDs
- **WHEN** retrieval is requested with active IDs `{A, B, C}` and database rows include references to `D`
- **THEN** returned maps include only edges where both endpoints are in `{A, B, C}`

### Requirement: Reconciliation SHALL remove stale references absent from Jira payload
The system SHALL provide a scrub operation that accepts active Jira release IDs and removes dependency and co-release rows where either endpoint no longer exists in the active set.

#### Scenario: Scrub deletes stale edges for removed release
- **WHEN** active Jira IDs no longer include `X` and relationship tables still contain rows referencing `X`
- **THEN** all dependency and co-release rows containing `X` are deleted

### Requirement: Database access SHALL be encapsulated in database.py functions
The system SHALL execute SQL, connection handling, cursor management, initialization, CRUD, and reconciliation logic only through dedicated functions in `database.py` and SHALL keep route handlers free of direct SQL.

#### Scenario: Route layer delegates database operations
- **WHEN** release relationship APIs are invoked
- **THEN** handlers call database.py interface functions and do not execute inline SQL
