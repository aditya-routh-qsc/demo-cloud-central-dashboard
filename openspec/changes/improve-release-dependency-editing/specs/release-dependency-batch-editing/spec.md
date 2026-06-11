## ADDED Requirements

### Requirement: Release Tab Edit Modal Entry
The system SHALL provide an Edit action in the Release tab that is usable with selected release rows and opens a dependency editing modal.

#### Scenario: Edit opens modal for selected releases
- **WHEN** one or more release rows are selected and the user activates Edit
- **THEN** the system opens the dependency editing modal scoped to the selected release set

#### Scenario: Edit is not actionable without selection
- **WHEN** no release rows are selected
- **THEN** the Edit action MUST be disabled or otherwise prevent opening the modal

### Requirement: Dual Directional Dependency Tables
The modal SHALL provide two editable tabs, Depends On and Depended By, each rendering the union of related releases across selected releases with relationship attribution metadata.

#### Scenario: Depends On tab shows outgoing relationships
- **WHEN** the user opens the Depends On tab
- **THEN** the table lists releases that any selected release depends on, including release name, release date, tooltip attribution, and remove action

#### Scenario: Depended By tab shows incoming relationships
- **WHEN** the user opens the Depended By tab
- **THEN** the table lists releases that depend on any selected release, including release name, release date, tooltip attribution, and remove action

### Requirement: Staged Add And Remove Behavior
Dependency add and remove actions in the modal SHALL update staged state only and MUST NOT persist to database until Apply Changes is executed.

#### Scenario: Remove stages deletion only
- **WHEN** the user removes a row in either modal tab
- **THEN** the row removal is reflected in staged modal data and no database mutation occurs

#### Scenario: Add panel submit stages additions only
- **WHEN** the user opens Add, selects one or more releases, and clicks Submit
- **THEN** the selections are added to staged modal data, the add panel closes, and no database mutation occurs

#### Scenario: Duplicate additions are ignored
- **WHEN** the user submits releases that already exist in staged relationships
- **THEN** only missing relationships are added and existing ones remain unchanged without error

### Requirement: Add Dependency Search Scope
The Add Dependency suggestion list SHALL exclude currently selected releases and may include already-linked releases.

#### Scenario: Selected releases are excluded from suggestions
- **WHEN** the add suggestion list is rendered
- **THEN** releases currently selected in the Release table are not shown as selectable candidates

#### Scenario: Already-linked releases remain visible
- **WHEN** the add suggestion list is rendered
- **THEN** releases already linked in staged or persisted relationships may still appear and are handled by duplicate-skip logic on submit

### Requirement: Dirty-State Controlled Modal Actions
Reset and Apply Changes controls SHALL be disabled by default and enabled only when staged state differs from persisted baseline.

#### Scenario: Buttons start disabled
- **WHEN** the modal first opens with no staged edits
- **THEN** Reset and Apply Changes are disabled

#### Scenario: Buttons enable after net staged changes
- **WHEN** the user adds or removes dependencies producing staged state differences
- **THEN** Reset and Apply Changes become enabled

#### Scenario: Buttons return disabled after successful apply
- **WHEN** Apply Changes succeeds and staged state matches persisted truth
- **THEN** Reset and Apply Changes are disabled

### Requirement: Transactional Apply Changes
Apply Changes SHALL persist all staged dependency updates atomically and SHALL rollback all updates on failure.

#### Scenario: Apply persists atomically with loading feedback
- **WHEN** the user clicks Apply Changes with staged edits
- **THEN** the system shows a loading indicator, commits all staged updates in one transaction, and updates modal state to persisted truth on success

#### Scenario: Apply failure rolls back all updates
- **WHEN** an error occurs during apply processing
- **THEN** no staged update is persisted, an error message is shown, and staged edits remain available for retry or reset

### Requirement: Reset Restores Persisted Truth
Reset SHALL discard all staged edits and reload modal tables from currently persisted dependency data.

#### Scenario: Reset discards staged additions and removals
- **WHEN** the user clicks Reset
- **THEN** both tabs re-render from database-truth relationships and all staged edits are cleared

### Requirement: Accessibility And Regression Safety
The modal workflow SHALL satisfy keyboard and focus accessibility requirements and SHALL preserve existing Release tab filter, sort, and selection behavior.

#### Scenario: Modal keyboard and focus behavior
- **WHEN** keyboard-only users interact with the modal
- **THEN** focus is trapped within the modal until close and controls are operable with keyboard navigation and labels

#### Scenario: Existing release table behavior remains stable
- **WHEN** users continue using Release tab filtering, sorting, and row selection outside and after modal usage
- **THEN** existing behavior remains unchanged except for the addition of the Edit workflow
