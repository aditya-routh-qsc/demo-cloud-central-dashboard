## ADDED Requirements

### Requirement: Collapsible Sidebar Navigation
The dashboard SHALL provide a sidebar collapse/expand control that changes navigation presentation without changing active view behavior.

#### Scenario: Expanded mode shows icon and label
- **WHEN** the sidebar is in expanded mode
- **THEN** each navigation option displays both its icon and text label

#### Scenario: Collapsed mode shows icon-only navigation
- **WHEN** the user collapses the sidebar
- **THEN** each navigation option displays an icon-only presentation and remains selectable

#### Scenario: Navigation state remains stable while toggling
- **WHEN** the user toggles sidebar collapsed/expanded state
- **THEN** the currently active dashboard view remains active and focusable controls remain keyboard accessible

## MODIFIED Requirements

### Requirement: Always-Visible Sync Trust Indicator
The dashboard SHALL display sync status persistently in the global header. The status MUST include current runtime state, most recent known run outcome information, and a last update timestamp.

#### Scenario: Running sync is visible immediately
- **WHEN** runtime sync state indicates an active run
- **THEN** the header displays an in-progress status indicator without requiring manual page refresh

#### Scenario: Last run outcome remains visible when idle
- **WHEN** no sync is currently running and persisted run details exist
- **THEN** the header displays the latest run outcome summary and the most recent update timestamp for operator trust
