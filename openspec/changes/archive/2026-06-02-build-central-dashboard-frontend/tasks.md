## 1. Frontend Foundation and Delivery

- [x] 1.1 Create frontend asset structure (HTML, CSS, JS modules) and wire static hosting from FastAPI runtime.
- [x] 1.2 Add frontend dependency strategy for charting and graph visualization (CDN or vendored assets) and verify deterministic loading.
- [x] 1.3 Implement base app shell with global header, navigation tabs/routes, and desktop/mobile responsive scaffolding.

## 2. Global State, Sync Trust, and API Client

- [x] 2.1 Implement shared filter state model for search, status, assignee, board, and pagination inputs.
- [x] 2.2 Implement API client methods for `/api/sync/status`, `/api/sync/manual`, `/api/tickets`, `/api/metrics`, and `/api/network`.
- [x] 2.3 Implement always-visible sync header component with decoupled status polling and manual sync trigger handling.

## 3. Core Views and Data Rendering

- [x] 3.1 Implement Overview view with KPI cards and contract-aligned aggregate visualizations.
- [x] 3.2 Implement Network view with dependency graph rendering and node details panel.
- [x] 3.3 Implement Metrics view with story point and assignee workload analytics.
- [x] 3.4 Implement Ticket Explorer view with table rendering, filtering, and pagination controls.

## 4. Deep-Linking and Mobile Read-Only Behavior

- [x] 4.1 Add Jira deep-link action from ticket rows using ticket key and configured/derived Jira host.
- [x] 4.2 Add Jira deep-link action in relevant graph node detail contexts.
- [x] 4.3 Enforce mobile read-only summary mode by hiding heavy interaction modules and preserving essential KPI/sync context.

## 5. Validation, Hardening, and Documentation

- [x] 5.1 Verify frontend behavior against API contract examples and error behavior expectations.
- [x] 5.2 Add smoke checks for unified filter persistence across views and sync-state visibility during active/idle runtime states.
- [x] 5.3 Document frontend run instructions, known limits (mobile read-only), and operational troubleshooting notes.
