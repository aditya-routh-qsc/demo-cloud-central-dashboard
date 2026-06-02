## ADDED Requirements

### Requirement: Jira GET requests SHALL implement transient-failure retries
The extraction service SHALL retry transient Jira GET failures for status codes 429, 502, 503, and 504 using exponential backoff with an upper retry bound.

#### Scenario: Temporary 503 during board discovery
- **WHEN** the first board discovery request returns HTTP 503 and a subsequent retry succeeds
- **THEN** extraction continues successfully without recording a terminal board-discovery failure

#### Scenario: Repeated 429 responses exceed retry budget
- **WHEN** Jira continues returning HTTP 429 beyond the configured retry limit
- **THEN** extraction records a partial error for the affected operation and continues processing remaining work

### Requirement: Jira requests SHALL use shared HTTP session reuse
The extraction service MUST perform Jira API calls through a shared requests session to reuse pooled HTTP connections during a run.

#### Scenario: Multiple issue detail requests in one run
- **WHEN** many issue details are fetched concurrently for one extraction run
- **THEN** the service uses one shared session-backed client path instead of creating independent non-pooled requests per call

### Requirement: Retry behavior SHALL preserve deterministic failure reporting
Retries MUST be transparent to output semantics and SHALL emit a single compact partial error only after retry exhaustion.

#### Scenario: Transient failures eventually recover
- **WHEN** a request fails transiently and succeeds within retry budget
- **THEN** no terminal partial error is recorded for that request

#### Scenario: Transient failures do not recover
- **WHEN** all retries fail for a request
- **THEN** one partial error is recorded with operation context and the run continues where possible
