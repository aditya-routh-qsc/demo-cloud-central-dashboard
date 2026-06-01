## Context

Phase 1 of the centralized Q-SYS Cloud dashboard requires a backend extraction layer that can reliably fetch raw team, timeline, and dependency signals from Atlassian cloud sources. The current workspace has no existing extraction capability spec, so this change introduces the foundational contract and implementation direction.

Constraints are intentionally strict:
- Use procedural/functional Python only (no custom classes).
- Use only `requests` and `python-dotenv` as external packages.
- Credentials must come from `.env` and never be hardcoded.
- Output must be JSON-compatible and stable for downstream pipeline use.
- Code and extraction paths must be beginner-readable with explanatory inline comments.

## Goals / Non-Goals

**Goals:**
- Provide a single service module API for Confluence roster retrieval, Jira timeline/progress retrieval, and Jira dependency/blocker mapping.
- Standardize request behavior with fixed Jira field lists and environment-configurable timeout (default 10 seconds in code).
- Ensure resilient orchestration through partial failure handling that records errors while still returning successful sections.
- Include metadata (`fetched_at`, `partial_errors`) in the aggregated output for observability.
- Provide usage-friendly runtime output in the module entrypoint: concise summary counts plus a formatted sample snippet.
- Make feature behavior easy to understand for beginners through clear comments and predictable return contracts.

**Non-Goals:**
- No HTML/XHTML parsing or normalization of Confluence roster content in this phase.
- No persistence layer, cache, queueing, or background scheduling.
- No Jira write operations (create/update/transitions).
- No web server endpoint exposure in this phase.
- No Atlassian SDK wrappers or additional third-party dependencies.

## Decisions

1. Functional service API shape
- Decision: Implement five standalone functions: `_get_auth`, `fetch_team_rosters`, `fetch_pod_timelines`, `fetch_cross_team_dependencies`, and `get_all_live_atlassian_data`.
- Rationale: This preserves strict non-OOP requirements and keeps function-level testing straightforward.
- Alternatives considered:
  - Class-based service object: rejected due to explicit architectural constraint.
  - Single monolithic function: rejected due to lower maintainability and testability.

2. Authentication and configuration handling
- Decision: Load configuration via `python-dotenv` from `.env` with required variables (`ATLASSIAN_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_TOKEN`) and optional timeout variable.
- Rationale: Keeps credentials outside source and supports local/dev variation.
- Alternatives considered:
  - Hardcoded values: rejected for security reasons.
  - OS-only environment variables without dotenv: rejected for poorer local onboarding.

3. Request timeouts and reliability
- Decision: Use timeout from environment when present, fallback to hardcoded 10 seconds.
- Rationale: Avoids indefinite hangs while allowing environment tuning for network conditions.
- Alternatives considered:
  - Infinite timeout: rejected for operational risk.
  - Hardcoded-only timeout: rejected for lack of configurability.

4. Jira payload minimization
- Decision: Always request fixed fields for Jira search calls.
  - Timeline fields: key, summary, timeoriginalestimate, timespent.
  - Dependency fields: key, summary, status, issuelinks.
- Rationale: Reduces payload size, improves stability of extraction, and avoids hidden coupling to unrelated fields.
- Alternatives considered:
  - Fetch all fields: rejected due to larger payload and noisier parsing.

5. Time/progress normalization
- Decision: Convert Jira seconds to day values in extractor output and compute progress safely with null/zero fallback to 0.
- Rationale: Dashboard consumers need comparable day-level metrics and deterministic behavior under missing fields.
- Alternatives considered:
  - Keep raw seconds only: rejected due to poorer readability for reporting users.

6. Aggregation and partial-failure strategy
- Decision: Aggregator executes feature calls sequentially with localized error capture, appending human-readable entries to `partial_errors` while returning an overall payload.
- Rationale: Dashboard availability should degrade gracefully instead of failing hard.
- Alternatives considered:
  - Fail-fast on first error: rejected because one upstream outage should not hide all data.

7. Developer-facing documentation in code and runtime output
- Decision: Include concise inline comments for each JSON path extraction and provide an executable `__main__` block that prints summary counts plus formatted snippet.
- Rationale: Helps beginner developers validate behavior quickly and understand extraction mapping.
- Alternatives considered:
  - Minimal comments only: rejected due to explicit documentation requirement.

## Risks / Trade-offs

- [Custom Jira link type naming can vary by instance] -> Mitigation: Normalize using both inward/outward descriptions and include raw link type text in output for traceability.
- [Confluence page body can be large or structurally inconsistent] -> Mitigation: Return raw body payload without attempting transformation in Phase 1.
- [Rate limiting or transient network failures] -> Mitigation: Timeout enforcement plus section-level error capture in aggregator.
- [Metric ambiguity for day conversion policy] -> Mitigation: Document conversion assumption directly in code comments and spec acceptance criteria.
- [Beginner readability vs concise code] -> Mitigation: Favor explicit variable naming and targeted comments over dense one-liners.

## Migration Plan

- Add `services.py` with the defined function contracts.
- Ensure `.env` contains required Atlassian credentials and optional timeout.
- Execute module directly (`python services.py`) using placeholder test inputs to verify connectivity and payload shape.
- Validate output sections (`teams`, `timelines`, `dependencies`) and metadata (`fetched_at`, `partial_errors`) against expected format.
- Rollback strategy: remove new module and associated invocation from operational workflows if API integration causes instability.

## Open Questions

- Which explicit day conversion basis should be authoritative for timeline metrics (8-hour workday vs 24-hour day)?
- Should timeout env variable name be fixed as `ATLASSIAN_TIMEOUT_SECONDS` or another naming standard already used by the team?
- Should summary snippet in `__main__` display first item from each section or a unified condensed preview object?
