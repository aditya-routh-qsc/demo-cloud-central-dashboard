## Why

The Release tab currently supports selection and relationship viewing, but there is no structured batch workflow to stage and review dependency edits before persisting. This causes risky direct edits and prevents users from safely applying coordinated dependency changes across multiple releases.

## What Changes

- Add a Release-tab Edit action that opens a modal-based dependency editor for one or more selected releases.
- Provide two editable modal tabs: Depends On and Depended By, each with release name, release date, relationship-context tooltip, and per-row remove actions.
- Add an inline Add Dependency flow in each tab with search, suggestions, multi-select, and staged submit behavior.
- Introduce staged edit state in the frontend so add/remove actions are non-persistent until explicit apply.
- Add Reset and Apply Changes controls with disabled-by-default behavior, dirty-state enabling, loading indicator during apply, and post-apply state reset.
- Add transactional backend apply behavior for batch dependency updates with rollback on failure.
- Preserve existing Release tab sorting/filtering/selection behavior and dashboard visual consistency.

## Capabilities

### New Capabilities
- `release-dependency-batch-editing`: Modal-based staged editing workflow for release dependencies, including add/remove staging, reset, and transactional apply.

### Modified Capabilities
- None.

## Impact

- Frontend: Release tab UI/state logic in the dashboard interface (modal, tabs, staged edits, tooltip, loading/empty/error states, accessibility wiring).
- Backend/API: Batch apply endpoint/service/data-layer support for all-or-nothing dependency updates.
- Persistence: Release dependency records updated only on Apply Changes, never during staging.
- Tests: New frontend/backend/integration regression coverage for modal behavior, transactional updates, and stability of current Release table behavior.
