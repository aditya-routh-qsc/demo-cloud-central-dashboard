## ADDED Requirements

### Requirement: Mobile Dependency Summary View
For mobile viewport breakpoints, the dashboard SHALL provide a summary dependency module instead of the full interactive graph canvas.

#### Scenario: Mobile renders summary instead of graph
- **WHEN** the client viewport matches mobile breakpoint rules
- **THEN** the network tab shows dependency summary content and suppresses full graph interactions

### Requirement: Mobile Summary Includes Core Dependency Signals
The mobile dependency summary SHALL expose key operational dependency signals sufficient for quick triage.

#### Scenario: Core metrics are visible on mobile
- **WHEN** dependency data is available
- **THEN** the summary displays at least blocker totals and inter-team versus intra-team counts

### Requirement: Explicit Network Empty-State Messaging
The dashboard SHALL distinguish between dependency absence, mobile summary mode, and data/load failures in network empty states.

#### Scenario: No dependencies state is explicit
- **WHEN** dependency data loads successfully and has zero edges
- **THEN** the network surface shows a no-dependencies message rather than a generic failure message

#### Scenario: Load failure is explicit
- **WHEN** dependency data cannot be loaded or rendered
- **THEN** the network surface shows an error-specific message with operator guidance
