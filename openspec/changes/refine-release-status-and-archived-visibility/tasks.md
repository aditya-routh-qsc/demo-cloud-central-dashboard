## 1. Release Edit Gating

- [x] 1.1 Update Release Edit button disabled state to require at least one selected row checkbox.
- [x] 1.2 Preserve accessible affordance text/aria state for disabled Edit action.

## 2. Planned + Overdue Status Semantics

- [x] 2.1 Remove Overdue as a standalone status option from Release table status dropdown generation.
- [x] 2.2 Update table filtering so Planned selection includes both Planned and Overdue rows.
- [x] 2.3 Update graph filtering so Planned selection includes Overdue nodes.
- [x] 2.4 Remove Archived and Overdue options from graph filter UI and defaults.

## 3. Archived Visibility Exclusion

- [x] 3.1 Add backend response filtering to exclude archived releases from `/api/releases` outputs.
- [x] 3.2 Apply archived exclusion consistently in release relationship endpoints before active ID derivation.
- [x] 3.3 Keep archived persistence behavior unchanged in database layer.

## 4. Validation And Regression Coverage

- [x] 4.1 Update frontend contract tests for planned/overdue semantics and graph status option set.
- [x] 4.2 Add backend tests validating archived release exclusion behavior.
- [x] 4.3 Run targeted tests for release endpoint and release-tab UI contract assertions.
