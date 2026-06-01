## Context

Runtime evidence shows a mixed state: Kanban board discovery is healthy at scale, but Jira search compatibility blocks timeline/dependency/detail retrieval and Confluence defaults still rely on placeholder IDs. At the same time, TLS warning suppression is globally active in code, reducing visibility in environments where transport risk should be explicit.

This change unifies compatibility handling and TLS warning policy while preserving existing output contracts and procedural architecture.

## Goals / Non-Goals

**Goals:**
- Keep one Jira search helper for all search modes and add compatibility fallback from /rest/api/3/search/jql to /rest/api/3/search for 400/404/405/410 scenarios.
- Ensure partial error diagnostics include query mode, endpoint attempted, status, and upstream payload details.
- Keep environment-driven runtime inputs and strengthen startup diagnostics for placeholder values.
- Replace unconditional urllib3 warning suppression with explicit environment-controlled policy.
- Add environment-aware suppression guardrails and compact startup status showing verify/suppression/environment modes.
- Preserve deterministic output keys and compact phase-tagged error semantics.

**Non-Goals:**
- Rewriting transport stack away from requests.
- Introducing async worker architecture.
- Changing business semantics of timeline/dependency extraction.

## Decisions

1. Compatibility fallback in shared search helper
- Decision: Use shared helper with endpoint sequence and compatibility-code fallback.
- Rationale: Prevents drift across timeline, dependency, and detail-batch logic.
- Alternatives considered:
  - Per-flow endpoint handling: rejected for inconsistency risk.

2. Compatibility diagnostics contract
- Decision: Include query_mode, method, endpoint path, status, and upstream detail snippet in query errors.
- Rationale: Operators need actionable failure context, not generic HTTP errors.
- Alternatives considered:
  - Generic exception passthrough: rejected due to low debuggability.

3. TLS warning suppression policy separation
- Decision: Separate warning suppression control from verify toggle using dedicated env flags.
- Rationale: verify=false and warning suppression are distinct concerns.
- Alternatives considered:
  - Keep suppression unconditional: rejected due to hidden risk in production-like environments.

4. Environment-aware suppression guardrail
- Decision: Suppress warnings only when explicitly enabled and policy permits current environment, with optional explicit override in production-like mode.
- Rationale: Balances local practicality with security observability.
- Alternatives considered:
  - Hard deny in production with no override: rejected for emergency debugging edge cases.

5. Startup diagnostic compact status line
- Decision: Emit one status line for environment mode, TLS verify mode, and suppression mode before run.
- Rationale: Faster operator triage and easier support handoff.
- Alternatives considered:
  - Multi-line verbose diagnostics only: rejected for log noise.

## Risks / Trade-offs

- [Fallback may mask root cause if both endpoints fail differently] -> Mitigation: include per-endpoint attempt diagnostics in final error.
- [Suppression policy complexity may confuse operators] -> Mitigation: emit explicit startup status and conflict warnings.
- [Stricter input warnings may be perceived as noisy] -> Mitigation: keep warnings compact and actionable.

## Migration Plan

- Add dedicated TLS warning suppression policy helpers and replace unconditional disable_warnings call.
- Refactor Jira search helper fallback and diagnostics payload formatting.
- Keep all search flows routed through same helper.
- Improve runtime input warnings and startup status output.
- Validate scenarios A-D from acceptance criteria and confirm deterministic outputs.

## Open Questions

- Which env key should define environment mode canonically (APP_ENV vs ATLASSIAN_ENV)?
- Should compatibility fallback attempt GET for legacy tenants or remain POST-only with path fallback?
- What maximum diagnostic payload snippet length is acceptable for logs?
