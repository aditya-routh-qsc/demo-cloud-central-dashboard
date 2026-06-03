## MODIFIED Requirements

### Requirement: Unified Global Filters Across Dashboard Views
The dashboard SHALL provide one shared filter model across overview, dependency network, metrics, and ticket explorer views. Filter controls MAY be presented in a collapsible region, but the current filter state MUST persist while navigating between views and while the region is collapsed during the same session.

#### Scenario: Filter state persists on navigation
- **WHEN** a user applies filter values and switches between dashboard views
- **THEN** the same effective filter state remains active and is reflected consistently in each view's data

#### Scenario: Collapsing filters does not clear selection state
- **WHEN** a user collapses the advanced filter region after setting filter values
- **THEN** the filter selections remain applied even though the controls are hidden

#### Scenario: Filter reset propagates everywhere
- **WHEN** a user performs a global filter reset action
- **THEN** all views return to unfiltered state and subsequent API requests omit filter-specific query parameters
