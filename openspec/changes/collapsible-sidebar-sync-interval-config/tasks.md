## 1. Frontend Sidebar UX

- [x] 1.1 Update sidebar navigation markup to include icon and label spans for each tab button.
- [x] 1.2 Add a sidebar toggle control in the dashboard shell and wire click handler to frontend state.
- [x] 1.3 Implement collapsed/expanded CSS states so collapsed mode shows icons only and expanded mode shows icon+text.
- [x] 1.4 Verify active-tab behavior and keyboard accessibility remain correct in both sidebar states.

## 2. Last Update Time Visibility

- [x] 2.1 Extend sync status rendering logic to compute and display a clear last update timestamp in the header/sync chip area.
- [x] 2.2 Add formatting/empty-state handling for missing timestamp values.
- [x] 2.3 Confirm timestamp visibility updates correctly after manual and scheduled sync events.

## 3. Configurable Sync Interval

- [x] 3.1 Add `SCHEDULED_SYNC_INTERVAL_MINUTES` to `.env` and config parsing utilities with integer validation and bounds checks.
- [x] 3.2 Update scheduler initialization to consume configured interval instead of hard-coded cadence.
- [x] 3.3 Add warning logs and fallback behavior for invalid or missing interval configuration.

## 4. Verification

- [x] 4.1 Run backend smoke checks for scheduled sync timing configuration and startup behavior.
- [x] 4.2 Validate frontend behavior for sidebar collapse/expand and last update timestamp display.
- [x] 4.3 Run OpenSpec validation for the change artifacts and resolve any schema/lint issues.
