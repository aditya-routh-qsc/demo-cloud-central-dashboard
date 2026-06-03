## Why

The dependency graph still leaves room for misinterpretation: bidirectional relations such as "Relates to" can look directional, isolated tickets add noise to the network view, and some ticket types are not immediately obvious at a glance. This change improves graph trust and scanability so users can understand dependency meaning faster without opening every node.

## What Changes

- Treat `Relates to` as a bidirectional relationship in the network graph.
- Remove arrowheads for bidirectional dependency edges so direction is not implied where none exists.
- Hide tickets that have no dependency edges from the dependency graph to reduce visual noise.
- Improve ticket type readability in the graph so issue types such as task and epic are easier to distinguish.
- Keep the node details panel as a fallback for deeper inspection while making graph-level ticket type cues stronger.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `central-dashboard-frontend-interface`: Extend dependency graph behavior to represent bidirectional relations without arrows, suppress isolated graph nodes, and make ticket type cues more visible and distinguishable.

## Impact

- Frontend graph rendering updates in `frontend/app.js` and associated legend/style handling in `frontend/style.css` if additional cues are needed.
- Network payload interpretation may need to distinguish bidirectional relation semantics from directional ones.
- Contract documentation and smoke checks may need updates if graph node inclusion rules change.
