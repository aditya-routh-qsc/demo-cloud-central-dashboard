## Why

The current dashboard shell uses a centered horizontal tab bar and a permanently expanded filter strip, which consumes valuable vertical space and makes the interface feel crowded as more controls are added. A compact side navigation and collapsible filter area would improve scanability, reduce chrome noise, and make the dashboard easier to use on smaller screens without changing the underlying data model.

## What Changes

- Replace the mid-page horizontal view switcher with a left-aligned side navigation for Overview, Network, Metrics, and Tickets.
- Add a collapsible search filter region so advanced filters can be hidden when not needed while keeping the primary search field visible.
- Preserve the shared filter state and view switching behavior across the new shell layout.
- Provide a responsive fallback so the navigation and filter disclosure remain usable on narrow viewports.
- Keep backend APIs and dashboard data contracts unchanged for the initial release.

## Capabilities

### New Capabilities
- `dashboard-shell-compact-navigation`: Defines a compact dashboard shell with side navigation for the four core views and a collapsible filter area that reduces visual clutter while preserving current dashboard state behavior.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extend the dashboard interface requirements to cover shell placement for navigation, collapsible filter affordances, and responsive layout behavior without altering the shared filter model.

## Impact

- Affected frontend modules: `frontend/index.html`, `frontend/app.js`, and `frontend/style.css`.
- Likely updates to smoke/contract validation in `scratch/smoke_frontend_contract.py`.
- Possible documentation updates in `docs/API_CONTRACT_SHEET.md` and `docs/FRONTEND_DASHBOARD_RUNBOOK.md` if the user-facing shell behavior is described there.
- No expected backend API changes for the first implementation pass.
