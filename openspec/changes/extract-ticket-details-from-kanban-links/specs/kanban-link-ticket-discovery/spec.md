## ADDED Requirements

### Requirement: Kanban link input acceptance
The system SHALL accept one or more Kanban board links as input and SHALL validate each link format before attempting discovery.

#### Scenario: Single valid link provided
- **WHEN** the user provides one supported Kanban board link
- **THEN** the system accepts the link and starts ticket discovery for that board

#### Scenario: Multiple links provided
- **WHEN** the user provides multiple supported Kanban board links
- **THEN** the system processes each link independently within the same run

#### Scenario: Invalid link format provided
- **WHEN** a provided link does not match supported Kanban board URL patterns
- **THEN** the system marks that link as invalid and records a validation error without terminating other link processing

### Requirement: Ticket discovery from board links
The system SHALL resolve each valid Kanban board link into a set of ticket identifiers and SHALL preserve source-link provenance for discovered tickets.

#### Scenario: Board resolves with ticket references
- **WHEN** a valid link points to a board with accessible tickets
- **THEN** the system returns discovered ticket identifiers linked to the source board URL

#### Scenario: Board resolves with zero tickets
- **WHEN** a valid link resolves successfully but no ticket references are available
- **THEN** the system returns an empty discovered set for that link and no fatal error

### Requirement: Ticket detail retrieval for discovered identifiers
The system SHALL fetch normalized ticket details for discovered identifiers and SHALL return only configured detail fields required by downstream consumers.

#### Scenario: Ticket details fetched successfully
- **WHEN** discovered ticket identifiers are accessible
- **THEN** the system returns normalized ticket detail objects containing required fields and stable keys

#### Scenario: Some tickets are inaccessible or missing
- **WHEN** one or more discovered identifiers cannot be retrieved
- **THEN** the system records per-ticket retrieval errors while still returning details for accessible tickets

### Requirement: Deterministic output contract with partial-error reporting
The system SHALL return a consistent JSON-compatible payload that includes discovery results, ticket details, and partial-error metadata.

#### Scenario: All links and tickets succeed
- **WHEN** all board links resolve and all discovered tickets are retrieved
- **THEN** the output includes populated ticket results and an empty error list

#### Scenario: Mixed success and failure
- **WHEN** some links or tickets fail while others succeed
- **THEN** the output still includes all top-level contract keys with accumulated partial errors for failed items

### Requirement: Timeout and safety controls for external requests
The system SHALL apply configured timeout values and SHALL avoid indefinite waiting when contacting external board/ticket endpoints.

#### Scenario: Timeout configured
- **WHEN** a timeout value is configured in environment settings
- **THEN** all external board/ticket requests use the configured timeout

#### Scenario: Upstream request exceeds timeout
- **WHEN** an upstream board or ticket endpoint exceeds configured timeout limits
- **THEN** the system records a timeout error for that unit of work and continues processing remaining links where possible

### Requirement: Operator usage guidance
The system SHALL provide clear usage instructions and examples for running link-based ticket discovery and interpreting results.

#### Scenario: Operator runs link-based extraction
- **WHEN** the operator executes the script/service with one or more board links
- **THEN** runtime output and documentation explain counts, successful discoveries, and reported partial failures
