## ADDED Requirements

### Requirement: Side Navigation for Core Views
The dashboard SHALL present the Overview, Network, Metrics, and Tickets views through a side navigation rail on desktop layouts. The navigation MUST clearly indicate the active view and switch the visible content without a full page reload.

#### Scenario: User switches to another core view
- **WHEN** a user selects a different view in the side navigation
- **THEN** the dashboard displays that view and marks the selection as active

#### Scenario: Active view remains discoverable
- **WHEN** the dashboard is showing any one of the four core views
- **THEN** the navigation MUST indicate which view is currently active

### Requirement: Collapsible Advanced Search Filters
The dashboard SHALL present the primary search field continuously and place advanced filters inside a collapsible region. Collapsing or expanding the advanced filter region MUST NOT reset the applied filter state.

#### Scenario: User collapses advanced filters
- **WHEN** a user collapses the advanced filter region
- **THEN** the primary search field remains available and the applied filter values remain active

#### Scenario: User reopens advanced filters
- **WHEN** a user expands the advanced filter region after applying filters
- **THEN** the previously selected filter values are still visible

### Requirement: Responsive Shell Fallback
The dashboard SHALL adapt the side navigation and filter controls for narrow viewports so the interface remains usable without horizontal overflow.

#### Scenario: Narrow viewport remains navigable
- **WHEN** the dashboard is rendered on a narrow screen
- **THEN** the user can still switch between the four core views and access the filter actions

#### Scenario: Compact layout avoids overflow
- **WHEN** the viewport width falls below the responsive threshold
- **THEN** the dashboard reflows the navigation and filter controls into a compact layout that fits the screen
