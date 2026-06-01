## Context

The current extraction workflow is oriented around direct ticket IDs, while day-to-day pod collaboration frequently shares Kanban board URLs that implicitly contain or reference ticket sets. The system needs a reliable path from board link input to normalized ticket detail output without forcing users to manually copy issue keys.

This change introduces link-driven discovery requirements and design constraints around external board access, pagination, and partial-failure handling so downstream reporting can consume consistent output.

## Goals / Non-Goals

**Goals:**
- Accept one or more Kanban board links as input to the extraction flow.
- Resolve board links into discoverable ticket identifiers.
- Fetch normalized ticket details for discovered identifiers.
- Provide stable output shape with explicit success/partial-failure metadata.
- Handle invalid links and inaccessible boards gracefully.

**Non-Goals:**
- Rebuilding Kanban UI functionality.
- Modifying ticket state or board configuration.
- Implementing long-term persistence or caching in this change.
- Introducing non-essential third-party SDK wrappers unless required by endpoint access constraints.

## Decisions

1. Input contract as list of board links
- Decision: Treat board links as the primary input boundary, supporting single and multiple URLs in one invocation.
- Rationale: Matches real workflow where teams share board links in messages/docs.
- Alternatives considered:
  - Ticket-key-only input: rejected because it preserves manual extraction burden.
  - Single-link only: rejected for batch workflow limitations.

2. Two-step extraction pipeline
- Decision: Separate processing into (a) board link resolution to ticket IDs and (b) ticket detail retrieval.
- Rationale: Improves testability and allows independent retries on resolution vs detail fetch phases.
- Alternatives considered:
  - One monolithic fetch: rejected due to poor observability and harder error handling.

3. Deterministic output schema
- Decision: Return a normalized payload with explicit collections for resolved tickets, unresolved links, and errors.
- Rationale: Downstream automation can rely on consistent keys regardless of partial failures.
- Alternatives considered:
  - Raw heterogeneous responses: rejected due to brittle consumer parsing.

4. Partial failure strategy
- Decision: Continue processing remaining links when one link fails; accumulate per-link errors.
- Rationale: Board/network issues should not block all extraction work.
- Alternatives considered:
  - Fail-fast: rejected for operational robustness reasons.

5. Guardrails for external access
- Decision: Include validation and sanitization for incoming links and enforce timeout controls for upstream calls.
- Rationale: Reduces malformed input risk and long-running request hangs.
- Alternatives considered:
  - Blind URL execution: rejected for safety and reliability concerns.

## Risks / Trade-offs

- [Board URL formats vary across products or tenants] → Mitigation: Define accepted patterns and explicit validation failures.
- [Permissions may allow board access but not all tickets] → Mitigation: Report per-ticket or per-link partial failures in output metadata.
- [Large boards may produce heavy pagination cost] → Mitigation: Add bounded pagination strategy and optional batch controls.
- [Link discovery logic may drift with upstream API changes] → Mitigation: Isolate resolver component and add contract tests for known sample URLs.

## Migration Plan

- Add new extraction functions that accept Kanban links and return normalized ticket details.
- Wire the new flow into existing script entrypoints without breaking direct-ticket workflows (if present).
- Add usage guidance and examples for link-based invocation.
- Validate with representative board URLs from development workspace.
- Rollback by disabling link-based entrypoint path while preserving existing direct-ticket behavior.

## Open Questions

- Which Kanban platform(s) are in immediate scope (Jira boards only vs multiple tools)?
- What minimum ticket detail fields are required by downstream consumers?
- Should duplicate ticket IDs across multiple links be deduplicated globally or preserved with link provenance?
- Is a strict URL allowlist required for security compliance?
