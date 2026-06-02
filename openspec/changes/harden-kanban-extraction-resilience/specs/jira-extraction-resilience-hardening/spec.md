## ADDED Requirements

### Requirement: TLS warning suppression SHALL be policy controlled
The extraction service SHALL NOT disable insecure TLS warnings globally at import time. The service MUST apply warning suppression only when runtime policy evaluation marks suppression as enabled.

#### Scenario: Suppression not requested
- **WHEN** TLS warning suppression is not requested in environment configuration
- **THEN** insecure TLS warnings remain visible and suppression mode is reported as disabled

#### Scenario: Suppression blocked in production-like mode
- **WHEN** suppression is requested in production-like mode without explicit override
- **THEN** suppression is not applied and a policy warning is emitted

### Requirement: Ticket results SHALL be deduplicated by ticket key
The extraction service SHALL upsert ticket results by unique ticket key across all processed board links and MUST merge source_links so one ticket can reference multiple boards.

#### Scenario: Same ticket discovered in multiple boards
- **WHEN** two board links resolve to the same ticket key
- **THEN** output contains one ticket record for that key and source_links includes both board links

#### Scenario: Unique tickets across boards
- **WHEN** multiple board links return non-overlapping ticket keys
- **THEN** output contains one record per ticket key with correct source_links membership

### Requirement: Dependency analysis SHALL tolerate malformed entries
Dependency analysis MUST use guarded key access and SHALL skip malformed dependency items rather than raising runtime exceptions.

#### Scenario: Dependency object missing expected fields
- **WHEN** a dependency item lacks ticket_key or relation fields
- **THEN** analysis continues and remaining valid dependencies are counted and returned

### Requirement: Pagination and numeric parsing SHALL be safe
The extraction service MUST safely parse numeric response fields, handling null or non-numeric values with fallback defaults.

#### Scenario: Jira total field is null
- **WHEN** board issue response has total set to null
- **THEN** extraction does not crash and pagination terminates safely

#### Scenario: Jira total field is non-numeric
- **WHEN** board issue response has total as a non-numeric string
- **THEN** extraction uses fallback parsing behavior and avoids ValueError/TypeError termination

### Requirement: Host validation SHALL support normalized equivalence
Kanban link validation MUST compare normalized hosts and MAY accept configured alias hosts for the same Jira tenant.

#### Scenario: Equivalent host formatting
- **WHEN** ATLASSIAN_URL and board link differ only by default port notation or host casing
- **THEN** link validation accepts the board link as same-tenant

#### Scenario: Allowed alias host
- **WHEN** board link host is present in configured alias host list
- **THEN** link validation accepts the board link
