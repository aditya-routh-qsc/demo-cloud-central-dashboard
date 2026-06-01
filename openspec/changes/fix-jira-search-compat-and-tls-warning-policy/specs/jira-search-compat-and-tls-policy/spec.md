## ADDED Requirements

### Requirement: Shared Jira search compatibility fallback
The system SHALL use a single shared Jira search helper for timeline, dependency, and detail-batch retrieval and SHALL retry with /rest/api/3/search when /rest/api/3/search/jql returns compatibility-related status codes.

#### Scenario: jql endpoint compatibility failure then fallback success
- **WHEN** /rest/api/3/search/jql returns 400, 404, 405, or 410 for a search request
- **THEN** the system retries using /rest/api/3/search and continues with successful results when fallback succeeds

#### Scenario: both endpoints fail
- **WHEN** both /rest/api/3/search/jql and /rest/api/3/search fail
- **THEN** the system records a single compatibility error containing attempted endpoints and status details

### Requirement: Query diagnostics detail contract
The system SHALL include query_mode, endpoint, method, status, and upstream detail snippet in query compatibility partial errors.

#### Scenario: timeline query failure
- **WHEN** timeline search fails due to compatibility or request errors
- **THEN** partial_errors includes a [query-compat] entry with query_mode=timeline and endpoint attempt metadata

#### Scenario: detail-batch query failure
- **WHEN** ticket detail batch search fails
- **THEN** partial_errors includes a [query-compat] or [detail-fetch] entry containing batch context and endpoint metadata

### Requirement: Runtime input warning hardening
The system SHALL keep runtime inputs environment-driven and SHALL emit [input-validation] warnings for placeholder Confluence page IDs and empty JQL values.

#### Scenario: placeholder Confluence page id
- **WHEN** ATLASSIAN_CONFLUENCE_PAGE_ID is placeholder or demo value
- **THEN** startup output includes [input-validation] warning and extraction continues with partial failure behavior

#### Scenario: empty timeline/dependency JQL
- **WHEN** ATLASSIAN_TIMELINE_JQL or ATLASSIAN_DEPENDENCY_JQL is empty
- **THEN** startup output includes [input-validation] warnings for each empty value

### Requirement: TLS warning suppression policy control
The system SHALL not suppress urllib3 insecure TLS warnings by default and SHALL only suppress them when explicit configuration enables suppression under allowed environment policy.

#### Scenario: default suppression disabled
- **WHEN** suppression flag is absent
- **THEN** insecure TLS warnings remain visible when verify is disabled

#### Scenario: suppression requested in production-like environment without override
- **WHEN** suppression is enabled but environment mode is production-like and override is absent
- **THEN** suppression is blocked and startup output includes policy warning

#### Scenario: suppression allowed in local/test environment
- **WHEN** suppression is enabled and environment mode is local/test
- **THEN** insecure TLS warnings are suppressed and startup status reports suppression enabled

### Requirement: Deterministic output and compact errors
The system SHALL preserve deterministic top-level output keys and compact phase-tagged errors across mixed-success runs.

#### Scenario: mixed success run
- **WHEN** some extraction phases fail and others succeed
- **THEN** output keeps expected keys and includes compact tagged errors: [input-validation], [query-compat], [board-discovery], [detail-fetch]

#### Scenario: systemic compatibility failure in detail batches
- **WHEN** first detail batch fails with systemic query compatibility error
- **THEN** the system stops further batches, avoids per-key error explosion, and records compact batch-level diagnostics

### Requirement: Acceptance scenario coverage
The system SHALL satisfy the following runtime acceptance scenarios.

#### Scenario: A - search fallback
- **WHEN** /search/jql fails with 400 and /search succeeds
- **THEN** timeline/dependency/detail retrieval use fallback results without fatal abort

#### Scenario: B - large board batching
- **WHEN** board discovery yields more than 1000 keys
- **THEN** detail retrieval uses batches and does not issue URI-too-large-prone single-key-list request

#### Scenario: C - placeholder Confluence page
- **WHEN** placeholder page ID is configured
- **THEN** warning and clean partial failure are emitted while process continues

#### Scenario: D - TLS suppression policy diagnostics
- **WHEN** suppression/verify/environment combinations vary
- **THEN** startup status reflects actual policy decision and warnings reflect conflicts or blocked suppression
