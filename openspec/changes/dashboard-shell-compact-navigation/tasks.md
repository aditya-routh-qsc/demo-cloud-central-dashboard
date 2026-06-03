## 1. Shell Layout

- [x] 1.1 Replace the centered horizontal view tabs with a left-side navigation rail for Overview, Network, Metrics, and Tickets.
- [x] 1.2 Wrap the search filters in a collapsible advanced-filter region while keeping the primary search field always visible.
- [x] 1.3 Preserve the existing active view state and filter state wiring so navigation and collapse actions do not reset dashboard data.

## 2. Responsive Behavior

- [x] 2.1 Add desktop layout styles for the side navigation shell and the content column.
- [x] 2.2 Add narrow-viewport fallback styles so the navigation and filter controls remain usable without horizontal overflow.
- [x] 2.3 Verify the collapsed filter region and responsive shell maintain readable spacing and accessible focus states.

## 3. Interaction Logic

- [x] 3.1 Update the tab-switching logic to drive the new side navigation while continuing to switch the four dashboard views.
- [x] 3.2 Add disclosure toggle behavior for the advanced filters without changing applied filter values.
- [x] 3.3 Confirm filter apply and reset actions still work when the advanced filter region is collapsed or expanded.

## 4. Validation and Documentation

- [x] 4.1 Update smoke/contract checks to assert the side navigation shell and collapsible filter behavior.
- [x] 4.2 Verify the dashboard renders correctly in desktop and mobile browser checks after the shell change.
- [x] 4.3 Update any user-facing dashboard documentation that describes the main navigation or filter layout.
