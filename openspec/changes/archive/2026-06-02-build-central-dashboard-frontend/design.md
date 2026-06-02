## Context

The backend currently provides stable dashboard APIs for sync status, ticket data, metrics, and dependency graph payloads. Users need a usable web interface for day-to-day operational visibility, but no frontend delivery layer exists yet. Recent decisions finalized interaction constraints: one unified filter system across pages, always-visible sync trust signals, Jira deep-linking from table and graph contexts, and mobile behavior constrained to read-only summaries.

## Goals / Non-Goals

**Goals:**
- Deliver a browser-based dashboard UI backed by existing FastAPI endpoints without changing backend contract shapes.
- Keep filter state global and consistent across overview, network, metrics, and ticket explorer views.
- Keep sync status visible in the global header and refresh it independently of heavier dashboard data calls.
- Provide direct Jira navigation for ticket rows and relevant graph node details.
- Provide a mobile-safe read-only summary mode that prioritizes performance and clarity.

**Non-Goals:**
- Redesigning extraction logic, persistence schema, or sync scheduler internals.
- Adding authentication/authorization in this change.
- Expanding mobile to full parity with desktop graph and table interactivity.
- Introducing backend endpoint versioning unless contract defects are found.

## Decisions

1. Frontend delivery model: static assets served by FastAPI.
- Rationale: simplest deployment path, keeps backend and frontend co-located for local/internal use.
- Alternatives considered:
  - Separate SPA deployment: better long-term isolation but adds hosting and CORS complexity now.
  - Server-rendered templates: reduces JS complexity but limits rich network visualization behavior.

2. Global state model: shared filter state and route-aware data orchestration.
- Rationale: unified filters are a hard requirement and must persist while users navigate views.
- Alternatives considered:
  - Per-page filter state: easier implementation but violates context preservation requirement.
  - URL-only state without in-memory store: sharable, but introduces excessive parsing churn for interactive controls.

3. Sync trust model: decoupled lightweight polling for `/api/sync/status`.
- Rationale: keeps header status fresh without forcing heavy data refetches for every poll cycle.
- Alternatives considered:
  - Full dashboard polling: simpler logic but unnecessary load and visual churn.
  - Manual refresh only: lower load but weak operational trust signal.

4. Jira deep-link strategy: derive canonical issue links from ticket key and known Atlassian host.
- Rationale: users need immediate navigation from analytics to source of truth.
- Alternatives considered:
  - Only board-level source links: provides context but not direct issue navigation.
  - Store precomputed issue URLs in backend: cleaner UI, but unnecessary contract expansion now.

5. Mobile strategy: responsive reduction to read-only summary module set.
- Rationale: aligns with explicit mobile requirement and avoids heavy graph/table UX on small screens.
- Alternatives considered:
  - Full responsive parity: high effort and poor usability for dense operational data.
  - Separate mobile app: out of scope and unnecessary for current adoption phase.

## Risks / Trade-offs

- [Risk] Graph rendering performance degrades for large dependency networks -> Mitigation: add node/edge count guardrails, lazy rendering, and optional reduced-detail modes.
- [Risk] Filter-cardinality combinations can trigger expensive repeated queries -> Mitigation: debounce filter inputs, use route-level caching, and avoid automatic full refetch on every keystroke.
- [Risk] Jira host derivation may fail for mixed-source datasets -> Mitigation: fall back to configured default host and expose clear error affordance for unresolved links.
- [Risk] Sync status could appear stale during backend contention -> Mitigation: surface last update timestamp and explicit running/queued states.
- [Trade-off] Mobile read-only mode reduces functionality -> Mitigation: keep key KPIs, freshness, and top risk summaries visible; defer advanced interactions to desktop.

## Migration Plan

1. Add frontend asset structure and static serving configuration in backend runtime.
2. Implement shell, global filter bar, route views, and sync header behavior.
3. Integrate API client layer and map payloads to overview, metrics, network, and ticket explorer UI modules.
4. Add Jira deep-link controls in table and node detail surfaces.
5. Add responsive rules to enforce mobile read-only summary mode.
6. Validate contract alignment against API contract sheet and smoke test manual sync interactions.
7. Rollback strategy: disable static route mount and keep backend API operation unchanged.

## Open Questions

- Should graph node deep-link open in new tab always, or follow a configurable preference?
- Should global filters be encoded in URL query params for shareable links in v1?
- Is there a desired upper bound for ticket rows returned to desktop table by default?
- Should mobile summary include only KPI cards or also a compact top-blockers list?
