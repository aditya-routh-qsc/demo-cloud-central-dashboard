## ADDED Requirements

### Requirement: Environment-Configurable Scheduled Sync Interval
The runtime scheduler SHALL read automated sync/database refresh interval from environment configuration.

#### Scenario: Scheduler interval is configured from environment
- **WHEN** the application starts with `SCHEDULED_SYNC_INTERVAL_MINUTES` set to a valid integer value
- **THEN** automated scheduled sync runs at the configured interval

#### Scenario: Invalid interval falls back safely
- **WHEN** `SCHEDULED_SYNC_INTERVAL_MINUTES` is missing, non-numeric, or out of allowed bounds
- **THEN** the application uses a documented default interval and records a warning in logs

### Requirement: Interval Configuration Is Operationally Discoverable
The deployment configuration SHALL expose a documented `.env` variable for scheduler interval tuning.

#### Scenario: Operators can configure interval without code changes
- **WHEN** an operator updates `.env` with a new valid `SCHEDULED_SYNC_INTERVAL_MINUTES` value and restarts the app
- **THEN** the next runtime uses the new interval for scheduled sync and database update cadence
