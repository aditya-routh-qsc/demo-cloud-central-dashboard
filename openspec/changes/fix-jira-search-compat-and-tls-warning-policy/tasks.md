## 1. Jira search compatibility fallback

- [x] 1.1 Refactor shared Jira search helper to try /rest/api/3/search/jql first and fallback to /rest/api/3/search for compatibility status codes (400/404/405/410).
- [x] 1.2 Ensure timeline, dependency, and detail-batch flows all call the same helper without custom endpoint logic.
- [x] 1.3 Preserve and expose per-attempt diagnostics (endpoint, status, method, query_mode).

## 2. Query diagnostics and compact errors

- [x] 2.1 Include upstream response detail snippets in [query-compat] errors when available.
- [x] 2.2 Keep phase-tagged partial error messages compact and operator-readable.
- [x] 2.3 Ensure systemic detail-batch compatibility failures stop further batch attempts to avoid error explosion.

## 3. Runtime input hardening

- [x] 3.1 Keep environment-driven runtime inputs for Confluence page ID, timeline JQL, dependency JQL, and Kanban links.
- [x] 3.2 Add explicit [input-validation] startup warnings for placeholder page IDs and empty JQL values.
- [x] 3.3 Add compact startup diagnostics line that identifies current input quality state.

## 4. TLS warning suppression policy

- [x] 4.1 Replace unconditional global urllib3.disable_warnings behavior with explicit suppression policy helper.
- [x] 4.2 Add suppression env flag and environment mode flag, with production-like guardrail and explicit override option.
- [x] 4.3 Print startup status line showing environment mode, TLS verify mode, and suppression mode.
- [x] 4.4 Add warning when suppression is requested but blocked by policy or unnecessary due to verify=true.

## 5. Acceptance verification

- [x] 5.1 Validate Scenario A: /search/jql fails with 400 and /search fallback succeeds.
- [x] 5.2 Validate Scenario B: board with >1000 discovered keys resolves via batches without URI-too-large-prone single request behavior.
- [x] 5.3 Validate Scenario C: placeholder Confluence page ID emits warning and clean partial failure.
- [x] 5.4 Validate Scenario D: TLS suppression policy diagnostics reflect actual verify/suppression/environment combinations.
