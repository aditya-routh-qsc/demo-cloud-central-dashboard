## Why

The dependency network is hard to interpret quickly because graph semantics are implicit, and ticket filtering still exposes a user-managed Rows control that can unintentionally hide available tickets. This change improves operator clarity by making graph encoding self-explanatory and ensuring ticket views always load the maximum supported dataset for the active filters.

## What Changes

- Add an always-visible desktop legend for dependency graph semantics (node type colors, edge type colors, and classification line styles).
- Enforce deterministic semantic mapping and fallback behavior for node and edge styling.
- Render separate edges when multiple dependency types exist for the same source-target ticket pair.
- Remove the Rows filter control from the UI and URL-driven filter state.
- Ensure ticket retrieval always requests the maximum supported row limit for filtered views.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extend requirements for dependency graph semantic legend behavior, deterministic node/edge styling, and fixed maximum ticket-row retrieval without user-managed rows filtering.

## Impact

- Frontend changes in `frontend/index.html`, `frontend/app.js`, and `frontend/style.css` for controls, graph rendering, and legend presentation.
- Backend ticket endpoint usage updates in `main.py` (request default/limit behavior alignment).
- Contract and behavioral validation updates in `docs/API_CONTRACT_SHEET.md` and `scratch/smoke_frontend_contract.py`.
