## Context

The current extraction service in [services.py](services.py) is functional, but several reliability and safety concerns can produce incorrect outputs or hide runtime signals. The flow currently performs per-request HTTP calls without retry/backoff, can duplicate tickets across boards, uses brittle parsing in dependency aggregation, and suppresses insecure TLS warnings globally at import time regardless of policy.

This design hardens the extraction runtime while preserving existing public output shape as much as possible. The goal is to improve correctness under multi-board inputs, resilience under transient Jira failures, and policy fidelity for TLS warning behavior.

## Goals / Non-Goals

**Goals:**
- Enforce TLS warning suppression only through explicit runtime policy decisions.
- Deduplicate ticket results by ticket key across all provided board links while preserving source provenance.
- Make parsing tolerant to malformed or partially populated Jira payloads.
- Improve upstream call reliability with retry and exponential backoff for transient status codes.
- Reuse HTTP connections via a shared requests session for better throughput.
- Keep output deterministic and compatible for downstream JSON consumers.

**Non-Goals:**
- Introducing persistent storage or scheduler orchestration in this change.
- Changing Atlassian credential model or secret management approach.
- Replacing requests with an async HTTP stack.

## Decisions

1. Policy-controlled TLS warning behavior
- Decision: Remove unconditional global warning suppression at module import and apply suppression only when runtime policy allows.
- Rationale: Preserves security signal visibility when suppression is disallowed.
- Alternatives considered:
  - Keep global suppression and log policy warnings: rejected because warnings are already hidden.

2. Ticket-level upsert semantics in aggregation
- Decision: Build a keyed aggregation map by ticket_key and merge source_links sets before final list materialization.
- Rationale: Prevents duplicate ticket records when the same ticket appears in multiple boards while preserving board membership.
- Alternatives considered:
  - Keep duplicates and dedupe later in consumers: rejected due to metric skew and downstream complexity.

3. Defensive parsing for dependency analysis
- Decision: Replace direct dictionary indexing with guarded reads and skip malformed dependency entries.
- Rationale: One malformed payload should not crash full extraction.
- Alternatives considered:
  - Fail-fast on malformed dependency objects: rejected for lower operational resilience.

4. Safe numeric conversion in pagination
- Decision: Introduce safe integer conversion helper with fallback defaults for null/non-numeric values.
- Rationale: Protects pagination loop from schema drifts and partial API anomalies.
- Alternatives considered:
  - Continue using int(raw): rejected due to TypeError/ValueError risk.

5. Host validation normalization and optional aliases
- Decision: Normalize hostname and default ports for equivalence checks and allow optional alias list via environment variable.
- Rationale: Avoids rejecting valid equivalent links while retaining tenant-scope safety.
- Alternatives considered:
  - Strict raw netloc equality: rejected as overly brittle.

6. Retry and backoff policy for transient failures
- Decision: Retry idempotent GET calls for 429/502/503/504 with capped exponential backoff and jitter.
- Rationale: Reduces noisy partial failures from temporary upstream instability.
- Alternatives considered:
  - No retries: rejected for unstable high-volume runs.

7. Shared requests Session for all Jira calls
- Decision: Create one session with default headers and adapter configuration, reused across API operations.
- Rationale: Improves performance via connection pooling and reduces TCP/TLS overhead.
- Alternatives considered:
  - Continue per-call requests.get: rejected due to repeated connection setup.

## Risks / Trade-offs

- [Aggressive retries can increase request volume under outage] -> Mitigation: cap retries and exponential backoff ceiling.
- [Alias host allowlist could broaden accepted links incorrectly] -> Mitigation: explicit env-based allowlist and normalization rules.
- [Dedupe merge can mask conflicting field values from different boards] -> Mitigation: stable merge policy and deterministic source_links union.
- [Session reuse may carry stale DNS/TCP state in long-lived processes] -> Mitigation: bounded process lifetime and adapter defaults.

## Migration Plan

1. Implement utility helpers for safe int conversion and normalized host comparison.
2. Remove global warning suppression and retain policy-driven suppression function.
3. Introduce shared session factory and centralized GET wrapper with retry/backoff.
4. Update Jira query code paths to use session wrapper.
5. Implement ticket upsert merge in result aggregation and preserve merged source_links.
6. Harden dependency analysis to tolerate missing keys and malformed relation records.
7. Validate output compatibility and count correctness on multi-board and mixed-quality payload scenarios.

Rollback strategy:
- Revert wrapper/session integration to direct requests.get.
- Revert dedupe aggregation to existing append behavior.
- Reintroduce previous host-validation and parsing behavior if needed.

## Open Questions

- Should retry configuration (attempt count/backoff max) be exposed through environment variables now or in a follow-up change?
- Should dedupe merge prefer newest updated timestamp when conflicting scalar fields differ?
- Should host aliasing accept wildcard domains or only exact normalized host entries?
