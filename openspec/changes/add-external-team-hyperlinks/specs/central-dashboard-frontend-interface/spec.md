## ADDED Requirements

### Requirement: External Jira Team Profile Link Rendering
The dashboard SHALL render Team Name as an actionable hyperlink in Teams dashboard views and Team Details views when a team profile URL is available.

#### Scenario: Team list row opens native Jira team profile in new tab
- **WHEN** a user clicks a Team Name in the Teams dashboard list and that team has a profile URL
- **THEN** the browser opens the team's native Jira profile URL in a new tab using `target="_blank"`

#### Scenario: Team details header indicates external navigation
- **WHEN** a user opens Team Details for a team with a profile URL
- **THEN** the team title/header includes a subtle external-link icon and clicking the team name opens the native Jira profile URL

### Requirement: Team Metadata Includes Canonical Profile Link
The backend SHALL persist and expose a canonical team profile URL for synchronized teams so frontend views can render outbound team links.

#### Scenario: Team profile URL is preserved during synchronization
- **WHEN** Jira team metadata is fetched and includes or can derive `organization_id`, `team_id`, and `cloud_id`
- **THEN** persistence stores a team profile link matching `https://home.atlassian.com/o/{organization_id}/people/team/{team_id}?cloudId={cloud_id}` or the upstream canonical URL if present

#### Scenario: Team profile URL survives upsert reruns
- **WHEN** synchronization is rerun for an existing team record
- **THEN** upsert behavior updates or retains the team profile URL without duplicate team rows

## MODIFIED Requirements

### Requirement: Contract-Aligned Data Consumption
The frontend SHALL consume existing backend APIs without requiring endpoint shape-breaking changes, and additive team metadata fields MUST be supported for link-enabled UI behavior.

#### Scenario: Core views map to existing contract payloads
- **WHEN** the dashboard loads overview, metrics, network, and ticket data
- **THEN** requests use currently documented endpoints and the UI renders from documented response fields plus additive team metadata fields such as `team_profile_url`

#### Scenario: Sync actions use existing manual trigger endpoint
- **WHEN** a user triggers manual sync from the dashboard
- **THEN** the frontend issues a request to the existing manual sync endpoint and updates status using the sync status endpoint
