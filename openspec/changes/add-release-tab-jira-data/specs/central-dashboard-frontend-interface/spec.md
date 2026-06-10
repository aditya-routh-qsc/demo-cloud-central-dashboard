## MODIFIED Requirements

### Requirement: Contract-Aligned Data Consumption
The frontend SHALL consume existing backend APIs without requiring endpoint schema changes for initial release, including the release-data surface backed by existing `services.py` retrieval logic.

#### Scenario: Core views map to existing contract payloads
- **WHEN** the dashboard loads overview, metrics, network, ticket, and release data
- **THEN** requests use currently documented endpoints and the UI renders from documented response fields without backend contract rewrites

#### Scenario: Sync actions use existing manual trigger endpoint
- **WHEN** a user triggers manual sync from the dashboard
- **THEN** the frontend issues a request to the existing manual sync endpoint and updates status using the sync status endpoint

#### Scenario: Release tab uses existing backend release integration
- **WHEN** a user opens the Release tab
- **THEN** the frontend retrieves release data from the already-implemented backend integration and renders it without modifying Jira fetch service logic
