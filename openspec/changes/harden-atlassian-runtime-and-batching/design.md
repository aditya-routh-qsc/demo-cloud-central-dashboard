## Context

Live execution showed several reliability and operability gaps in the current Atlassian extraction flow: oversized ticket-detail JQL requests trigger HTTP 414, some Jira search requests return HTTP 410 in this tenant, placeholder defaults produce false-failure noise, and TLS bypass mode is active in runtime. These issues collectively reduce confidence in dashboards and create repeated manual triage.

The change focuses on runtime hardening while preserving the existing procedural architecture and dependency constraints.

## Goals / Non-Goals

**Goals:**
- Prevent oversized detail fetch requests by batching ticket key lookups.
- Adopt Jira search request strategy that is accepted in the tenant for timeline/dependency and detail retrieval flows.
- Replace placeholder defaults with configuration-driven runtime inputs.
- Keep deterministic output contracts while improving partial-failure diagnostics.
- Keep TLS verification enabled by default and make insecure mode visibly temporary.

**Non-Goals:**
- Rebuilding extraction architecture into async workers.
- Adding persistence/cache layers.
- Expanding to non-Atlassian data sources.
- Adding third-party Atlassian SDK wrappers.

## Decisions

1. Batched detail retrieval
- Decision: Split discovered ticket keys into bounded chunks and perform multiple search requests.
- Rationale: Eliminates request URI overflow and allows partial progress on failed batches.
- Alternatives considered:
  - Single huge JQL request: rejected because it causes 414 at high scale.
  - One-request-per-key: rejected due to poor latency and rate-limit pressure.

2. Search request compatibility strategy
- Decision: Centralize Jira search invocation shape (method + path + payload/params) so timeline, dependency, and detail lookups use one compatible approach.
- Rationale: Avoids drift where one flow works and others fail with 410.
- Alternatives considered:
  - Per-call ad hoc request construction: rejected due to repeated compatibility bugs.

3. Runtime input source policy
- Decision: Main execution mode reads sample/runtime inputs from environment variables with explicit fallback labels indicating demo-only values.
- Rationale: Prevents accidental placeholder IDs and misleading failures during routine runs.
- Alternatives considered:
  - Hardcoded placeholders: rejected for operational confusion.

4. TLS and security signaling
- Decision: Keep verify=true default, allow temporary override through env, and emit clear warning in output when insecure mode is active.
- Rationale: Supports local unblock while preserving secure-by-default posture.
- Alternatives considered:
  - Always insecure mode: rejected for security risk.

5. Error observability structure
- Decision: Preserve deterministic top-level keys and attach compact per-phase error summaries (validation, board discovery, detail fetch, query compatibility).
- Rationale: Enables fast troubleshooting and stable downstream parsing.
- Alternatives considered:
  - Raw exception passthrough only: rejected due to noisy and inconsistent diagnostics.

## Risks / Trade-offs

- [Chunk size too large still risks request failures] -> Mitigation: Introduce configurable batch size with safe default and retries.
- [Tenant compatibility may change again] -> Mitigation: Keep search transport centralized behind one helper and integration test with known query.
- [More requests may increase rate-limit pressure] -> Mitigation: Add pacing/backoff hooks and capture 429 diagnostics.
- [Environment-driven runtime values may be missing] -> Mitigation: Validate required runtime inputs at startup with actionable errors.

## Migration Plan

- Add batched ticket detail fetch path and wire it into Kanban detail resolution.
- Refactor search helper to use tenant-compatible request strategy across all query flows.
- Move runtime defaults for Confluence page/JQL/board links to environment variables and document examples.
- Add security and compatibility warnings in runtime output.
- Validate against representative scenarios: large board, valid page/JQL, invalid link, and mixed-success detail fetch.

## Open Questions

- What is the preferred batch size limit for ticket key queries in this tenant?
- Should compatibility fallback include alternate Jira search endpoints automatically?
- Is insecure TLS mode allowed in CI or only local dev?
- Should runtime treat placeholder values as hard errors or soft warnings?
