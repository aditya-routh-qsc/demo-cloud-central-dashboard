## ADDED Requirements

### Requirement: Batched ticket detail retrieval
The system SHALL fetch ticket details in bounded batches when the discovered key set exceeds single-request limits, and SHALL aggregate successful records across batches.

#### Scenario: Large ticket key set
- **WHEN** discovered ticket keys exceed the configured batch threshold
- **THEN** the system issues multiple detail-fetch requests and returns a merged normalized result set

#### Scenario: One batch fails
- **WHEN** one detail batch request fails while others succeed
- **THEN** the system returns successful batch results and records partial errors for failed batches

### Requirement: Jira search request compatibility
The system SHALL use a tenant-compatible Jira search request strategy for timeline, dependency, and ticket detail lookup flows.

#### Scenario: Compatible search request
- **WHEN** the system executes timeline or dependency search in the configured tenant
- **THEN** the request shape is accepted and returns query results without compatibility errors

#### Scenario: Compatibility failure detected
- **WHEN** the active search strategy returns compatibility-related HTTP failures
- **THEN** the system records actionable diagnostics indicating query mode and endpoint used

### Requirement: Runtime input hardening
The system SHALL load Confluence page ID, timeline JQL, dependency JQL, and sample board links from environment configuration for non-demo execution.

#### Scenario: Runtime configuration provided
- **WHEN** required runtime inputs are supplied via environment values
- **THEN** the script executes extraction using configured values instead of placeholders

#### Scenario: Placeholder or missing runtime values
- **WHEN** runtime inputs are missing or recognized as placeholder/demo values
- **THEN** the script emits clear warnings and records input quality diagnostics

### Requirement: Secure TLS posture with explicit override visibility
The system SHALL keep TLS verification enabled by default and SHALL surface a clear runtime warning when insecure verification override is active.

#### Scenario: Secure default mode
- **WHEN** TLS override is not explicitly disabled
- **THEN** HTTPS requests verify certificates

#### Scenario: Insecure override mode
- **WHEN** TLS verification is disabled via environment override
- **THEN** runtime output includes an explicit warning that insecure mode is active

### Requirement: Deterministic error and output contract
The system SHALL maintain deterministic top-level output keys and SHALL include compact phase-specific partial error messages for validation, discovery, and detail retrieval.

#### Scenario: Mixed runtime outcomes
- **WHEN** some phases succeed and others fail
- **THEN** the output retains all contract keys and includes phase-tagged error entries in partial_errors

#### Scenario: Fully successful execution
- **WHEN** all configured inputs and upstream requests succeed
- **THEN** the output includes populated records with an empty partial_errors list
