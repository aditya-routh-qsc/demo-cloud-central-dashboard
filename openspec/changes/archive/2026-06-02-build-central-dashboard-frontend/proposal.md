## Why

The backend extraction, caching, and API contract are in place, but there is no operational web interface for stakeholders to consume the data. Building a dedicated frontend now enables the centralized dashboard outcome and turns cached dependency and metrics data into daily decision support.

## What Changes

- Build a production-ready web dashboard UI that consumes the existing API contract from `main.py`.
- Add a unified global filter bar shared across all dashboard pages to preserve context.
- Add always-visible global sync status in the header for trust and freshness awareness.
- Add Jira deep-links from ticket rows and relevant dependency graph nodes.
- Add a responsive mobile mode constrained to read-only summary views.
- Define frontend route-level views for overview, dependency network, metrics, and ticket exploration.

## Capabilities

### New Capabilities
- `central-dashboard-frontend-interface`: Browser-based dashboard experience for ticket metrics, dependency visualization, sync transparency, and ticket exploration across desktop and mobile.

### Modified Capabilities
- None.

## Impact

- Affected code: new frontend assets, static hosting wiring in FastAPI app, and API-consumption client logic.
- Affected APIs: no endpoint shape changes required; relies on current `/api/sync/status`, `/api/sync/manual`, `/api/tickets`, `/api/metrics`, `/api/network` contracts.
- Affected systems: local dashboard runtime now includes browser UI layer in addition to background sync and SQLite cache.
- Dependencies: frontend visualization/chart libraries and static asset pipeline decisions (CDN or bundled local artifacts).
