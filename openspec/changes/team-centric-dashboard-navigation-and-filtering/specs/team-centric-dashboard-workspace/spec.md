## ADDED Requirements

### Requirement: Teams Navigation and Dedicated Workspace
The dashboard SHALL provide a Teams option in the primary side navigation and SHALL route users to a dedicated Teams workspace view.

#### Scenario: Teams entry appears in primary navigation
- **WHEN** the dashboard shell is rendered
- **THEN** a Teams navigation option is visible alongside existing navigation options

#### Scenario: Teams route activates dedicated workspace
- **WHEN** a user selects the Teams navigation option
- **THEN** the main content region renders the Teams workspace template instead of ticket/network views

### Requirement: Team Roster View with External Member Links
The Teams workspace SHALL display valid teams and their members, and each member row SHALL provide an external Jira profile link that opens in a new browser tab with an external-link icon.

#### Scenario: Team roster list includes member links
- **WHEN** team and member data is available in cache
- **THEN** each member displays an actionable profile link and an external-link icon indicator

#### Scenario: Member link opens in separate tab
- **WHEN** a user clicks a member profile link
- **THEN** the browser opens the Jira profile URL in a new tab using target _blank semantics

### Requirement: Team Detail Tabs for Operational Views
Selecting a team SHALL open a detail surface with four tabs: Tickets Assigned, Work Done, Tickets Reported, and Timeline.

#### Scenario: Team detail exposes four required tabs
- **WHEN** a team is selected from the Teams workspace
- **THEN** the UI displays exactly the four required tabs and defaults to Tickets Assigned

#### Scenario: Assigned and reported tabs remain semantically distinct
- **WHEN** a user switches between Tickets Assigned and Tickets Reported
- **THEN** the UI differentiates assignment-based and reporter-based ownership with distinct visual styling

### Requirement: Team Timeline Visualization
The Timeline tab SHALL visualize workflow progression for tickets owned by team members using horizontal color-coded progress bars.

#### Scenario: Timeline renders standard status lanes
- **WHEN** timeline data is loaded for a selected team
- **THEN** bars represent at least To Do, In Progress, and Done categories with distinct colors

#### Scenario: Timeline shows loading skeleton before hydration
- **WHEN** timeline data is still being fetched from cache-backed API responses
- **THEN** the timeline area displays skeleton placeholders until final bars are rendered
