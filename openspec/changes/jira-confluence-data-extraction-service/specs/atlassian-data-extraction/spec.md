## ADDED Requirements

### Requirement: Secure Atlassian configuration and authentication
The system MUST load Atlassian configuration from environment variables and MUST NOT hardcode credentials. The service SHALL support `.env`-based local configuration using `python-dotenv`, and authentication SHALL be produced by a helper function reusable across API calls.

#### Scenario: Required credentials available
- **WHEN** the service loads environment configuration and all required values (`ATLASSIAN_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_TOKEN`) are present
- **THEN** the authentication helper returns a valid authentication object compatible with `requests`

#### Scenario: Required credential missing
- **WHEN** any required credential is missing or empty
- **THEN** the service surfaces a clear error message indicating which required configuration is missing

### Requirement: Team roster extraction from Confluence page body
The system SHALL fetch Confluence page content from `/wiki/api/v2/pages/{page_id}` with `body-format=storage` and SHALL return raw page body content needed for downstream parsing in later phases.

#### Scenario: Confluence page fetch succeeds
- **WHEN** `fetch_team_rosters(page_id)` is called with a valid page identifier and the API returns HTTP success
- **THEN** the function returns the raw XHTML/HTML storage body payload for that page in a JSON-compatible structure

#### Scenario: Confluence page fetch fails
- **WHEN** `fetch_team_rosters(page_id)` receives a non-success HTTP response or request exception
- **THEN** the failure is propagated to the aggregator path for partial error reporting without crashing the full process

### Requirement: Timeline extraction with fixed Jira fields and safe progress computation
The system SHALL execute Jira search using a provided JQL query and SHALL always request fixed Jira fields for timeline extraction. For each issue, the system SHALL extract key, summary, original estimate, spent time, and computed progress with safe defaults.

#### Scenario: Timeline query requests fixed fields only
- **WHEN** `fetch_pod_timelines(jql_query)` performs the Jira search call
- **THEN** the request includes a fixed fields list containing timeline-required fields and does not rely on fetching all fields

#### Scenario: Timeline issue has complete time metrics
- **WHEN** an issue has non-null `timeoriginalestimate` and `timespent`
- **THEN** the function returns day-level values and a computed progress percentage derived from those metrics

#### Scenario: Timeline issue has missing or zero estimate values
- **WHEN** `timeoriginalestimate` is null, missing, or zero
- **THEN** the function returns zero-safe day metrics and sets progress percentage to 0 instead of failing

### Requirement: Dependency extraction with blocker mapping
The system SHALL query Jira issues with fixed dependency fields and SHALL parse both inward and outward issue links to identify blocker relationships. Returned records SHALL include source issue data, target issue data, link description, and blocking issue status.

#### Scenario: Issue contains outward blocker link
- **WHEN** an issue contains an outward link representing a blocking relationship
- **THEN** the output includes a dependency record from source issue to target issue with link type text and target status

#### Scenario: Issue contains inward blocker link
- **WHEN** an issue contains an inward link representing that the source issue is blocked by another issue
- **THEN** the output includes a dependency record capturing source/target orientation and blocker status information

#### Scenario: Issue has no blocker links
- **WHEN** an issue has no `issuelinks` or only non-blocking link types
- **THEN** the issue contributes no dependency record and processing continues safely

### Requirement: Unified aggregation with metadata and partial failure reporting
The system SHALL provide an orchestrator that executes all extraction functions, returns a unified JSON-compatible payload, and captures per-section failures into metadata without terminating the entire result.

#### Scenario: All data sources succeed
- **WHEN** `get_all_live_atlassian_data(...)` executes and all upstream calls succeed
- **THEN** the response includes `fetched_at`, empty `partial_errors`, and populated `teams`, `timelines`, and `dependencies`

#### Scenario: One or more data sources fail
- **WHEN** any extraction function raises request or HTTP-related exceptions
- **THEN** the response still includes all top-level keys, records the failure details in `partial_errors`, and returns empty values only for failed sections

### Requirement: Environment-configurable timeout with safe default
The system SHALL support request timeout configuration from environment and SHALL default to 10 seconds when timeout is not configured.

#### Scenario: Timeout provided by environment
- **WHEN** a valid timeout value is present in environment configuration
- **THEN** Atlassian HTTP requests use that configured timeout value

#### Scenario: Timeout not provided
- **WHEN** timeout is missing from environment configuration
- **THEN** Atlassian HTTP requests use the in-code default timeout of 10 seconds

### Requirement: Beginner-focused feature documentation and usage output
The system SHALL include beginner-readable extraction comments and SHALL provide an executable module entrypoint that demonstrates how to run the service with placeholder arguments and inspect results quickly.

#### Scenario: Developer runs module directly
- **WHEN** the developer executes `python services.py`
- **THEN** the script prints concise summary counts plus a formatted sample snippet of extracted payload data

#### Scenario: Developer reviews extraction logic
- **WHEN** a developer reads the service functions
- **THEN** each JSON extraction path is documented with concise inline comments describing source field mapping intent
