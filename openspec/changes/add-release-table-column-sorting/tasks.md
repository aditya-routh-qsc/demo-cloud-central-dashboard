## 1. Sort State And Interaction Wiring

- [x] 1.1 Add Release table sort state model for active column and direction (`asc|desc|none`)
- [x] 1.2 Implement header click handling to cycle the same column through Ascending -> Descending -> Default
- [x] 1.3 Ensure selecting a new sortable column starts at ascending and updates active state

## 2. Sorting Utilities And Chronological Date Handling

- [x] 2.1 Add frontend sorting utility functions for string/text columns and shared comparator orchestration
- [x] 2.2 Add date-aware comparator logic for Release Date using parsed date values (not plain text)
- [x] 2.3 Preserve baseline unsorted row order and restore it when sort state returns to default

## 3. Header UI And Visual Indicators

- [x] 3.1 Update Release table header markup/classes to support clickable sortable headers
- [x] 3.2 Add ascending/descending indicator visuals on the active header and clear indicators in default mode
- [x] 3.3 Add/adjust CSS styling so sort affordances and active direction are visually clear and consistent

## 4. Validation And Documentation Sync

- [x] 4.1 Add/update frontend tests for tri-state header toggling and active indicator behavior
- [x] 4.2 Add/update tests for chronological Release Date sorting correctness
- [x] 4.3 Update `docs/CURRENT_BEHAVIOR_SPEC.md` to document sortable Release headers, sort-state behavior, and date-aware sorting