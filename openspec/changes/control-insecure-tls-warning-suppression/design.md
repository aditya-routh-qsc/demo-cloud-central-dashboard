## Context

The current code suppresses urllib3 insecure TLS warnings globally at import time. This improves readability in local environments with self-signed certificates, but it can also hide critical transport-security signals in production-like environments if enabled unintentionally.

A controlled design is needed so warning suppression is explicit, environment-gated, and auditable.

## Goals / Non-Goals

**Goals:**
- Keep secure behavior as default.
- Allow explicit warning suppression only when configured.
- Add environment-aware guardrails (for example: local/test allowed, production denied by default).
- Produce clear runtime diagnostics for TLS verify mode and warning suppression mode.
- Keep implementation minimal and compatible with existing procedural code.

**Non-Goals:**
- Replacing requests/urllib3 stack.
- Implementing enterprise certificate trust distribution.
- Auto-detecting every possible environment type beyond configurable flags.

## Decisions

1. Explicit suppression toggle
- Decision: Introduce a dedicated environment flag (for example ATLASSIAN_SUPPRESS_INSECURE_TLS_WARNING).
- Rationale: Separates warning visibility control from TLS verification control.
- Alternatives considered:
  - Always suppress warnings: rejected due to security observability risk.
  - Never suppress warnings: rejected because local/test logs become noisy.

2. Environment safety gate
- Decision: Gate suppression by environment mode (for example APP_ENV) with production-deny default unless an explicit override exists.
- Rationale: Prevents accidental suppression in high-risk environments.
- Alternatives considered:
  - No gating: rejected due to operational risk.

3. Startup diagnostics contract
- Decision: Print one compact startup line summarizing verify mode, suppression mode, and environment mode.
- Rationale: Operators can immediately see risky configuration combinations.
- Alternatives considered:
  - Silent behavior: rejected because misconfiguration is hard to detect.

4. Validation of conflicting configuration
- Decision: Emit explicit warning when suppression is enabled while TLS verification is enabled (no warning would normally appear).
- Rationale: Helps detect unnecessary or misunderstood config.
- Alternatives considered:
  - Ignore conflict: rejected due to debugging confusion.

## Risks / Trade-offs

- [Overly strict gating blocks legitimate local use] -> Mitigation: allow explicit non-production override flag.
- [Too many startup warnings cause noise] -> Mitigation: compact single-line status plus targeted warnings only on conflicts.
- [Users rely on old implicit behavior] -> Mitigation: provide migration notes and backward-compatible defaults where safe.

## Migration Plan

- Add new suppression configuration flags and helper function.
- Refactor warning suppression call to execute conditionally instead of at import-time unconditionally.
- Add startup TLS/suppression status output and conflict warnings.
- Validate local/test vs production-like settings with small runtime checks.
- Update .env guidance and runbook snippets.

## Open Questions

- Which environment variable should be authoritative for environment mode (APP_ENV, ENV, or ATLASSIAN_ENV)?
- Should suppression be hard-blocked in production or allowed only with a second explicit override?
- Do we want CI to behave as production or test for warning suppression policy?
