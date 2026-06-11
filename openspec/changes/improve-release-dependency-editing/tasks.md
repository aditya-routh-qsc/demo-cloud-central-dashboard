## 1. Release Tab Modal Entry And Layout

- [x] 1.1 Add Release-tab Edit button wired to current table checkbox selection state
- [x] 1.2 Implement modal container with two tabs (Depends On, Depended By) and footer actions (Reset, Apply Changes)
- [x] 1.3 Render tab tables with columns for release name, release date, info tooltip, and row-level remove action
- [x] 1.4 Add empty, loading, and inline error visual states for modal tables and add-dependency section

## 2. Staged State And Relationship Aggregation

- [x] 2.1 Add persisted snapshot state and separate staged state for modal edits
- [x] 2.2 Implement union aggregation logic across selected releases for both directional tabs
- [x] 2.3 Implement tooltip attribution mapping that identifies selected release(s) and direction for each displayed row
- [x] 2.4 Add normalization logic to enforce dedupe and direction synchronization across both tabs

## 3. Add And Remove Interaction Flows

- [x] 3.1 Implement row remove handlers that stage dependency deletions without persistence
- [x] 3.2 Implement Add Dependency panel with search input, suggestions dropdown, and multi-select candidates
- [x] 3.3 Enforce add suggestions scope by excluding currently selected releases while allowing already-linked options
- [x] 3.4 Implement Submit behavior to stage additions, close add panel, and silently skip duplicates

## 4. Dirty-State Controls, Reset, And Apply

- [x] 4.1 Implement dirty-state comparison and enable/disable behavior for Reset and Apply Changes buttons
- [x] 4.2 Implement Reset to discard staged edits and reload current persisted dependency truth
- [x] 4.3 Implement Apply Changes frontend workflow with loading indicator and success/error feedback
- [x] 4.4 Implement backend batch apply contract and atomic transaction with rollback on failure

## 5. Accessibility And Regression Safety

- [x] 5.1 Add modal keyboard navigation, focus trap, escape/close behavior, and aria labels for tabs/buttons/tooltips
- [x] 5.2 Verify Release tab sort/filter/selection behavior remains unchanged after modal integration
- [x] 5.3 Ensure modal open/close does not corrupt existing Release-tab local state or dataset refresh behavior

## 6. Validation And Documentation

- [x] 6.1 Add frontend tests for modal rendering, tab behavior, staged add/remove flows, and dirty-state button toggling
- [x] 6.2 Add backend/API tests for batch apply transaction success and rollback semantics
- [x] 6.3 Add UI tests for tooltip attribution, loading/error states, and keyboard accessibility baseline
- [x] 6.4 Add regression tests for existing Release tab filtering, sorting, and row selection behavior
- [x] 6.5 Update behavior documentation to describe staged editing semantics and apply/reset guarantees
