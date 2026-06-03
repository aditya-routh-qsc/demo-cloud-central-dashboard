## 1. Filter Model and Ticket Retrieval

- [x] 1.1 Remove Rows/page-size control from filter UI markup and related frontend element bindings.
- [x] 1.2 Remove row-count state from frontend filter model, URL serialization/deserialization, and reset paths.
- [x] 1.3 Update ticket query construction to always request maximum supported row limit.
- [x] 1.4 Align backend ticket endpoint default/guardrail behavior to preserve max-limit retrieval safety.

## 2. Graph Semantic Data and Styling

- [x] 2.1 Add normalized semantic mapping utilities for issue type, dependency type, and classification values.
- [x] 2.2 Extend graph element construction to include semantic data required for node and edge styling.
- [x] 2.3 Update edge identity generation to preserve separate edges for distinct dependency types on the same source-target pair.
- [x] 2.4 Implement deterministic node/edge style selectors with explicit unknown fallback styles.

## 3. Graph Legend UX

- [x] 3.1 Add dependency graph legend container and structure in network view markup.
- [x] 3.2 Add legend visual styles for node types, dependency types, and classification line-style semantics.
- [x] 3.3 Ensure legend content and graph style mappings share a single source of truth.

## 4. Validation and Contract Updates

- [x] 4.1 Update contract documentation for removed Rows filter and fixed max-row ticket retrieval behavior.
- [x] 4.2 Extend smoke/contract checks for no Rows control, no row-count URL parameter, and max-limit ticket requests.
- [x] 4.3 Add graph behavior validation for legend visibility, deterministic semantic mappings, fallback categories, and distinct multi-type edges.
- [x] 4.4 Perform manual desktop/mobile verification for filter behavior, graph semantics, and ticket visibility consistency.
