## Why

Current runtime behavior shows systemic extraction failures despite valid connectivity: Jira search compatibility errors prevent timeline/dependency/detail retrieval, placeholder runtime inputs cause avoidable Confluence failures, and global insecure TLS warning suppression reduces visibility of risky transport settings. This change is needed to restore reliable extraction while preserving clear security and operational diagnostics.

## What Changes

- Harden Jira search compatibility in one shared helper with fallback from /rest/api/3/search/jql to /rest/api/3/search when compatibility status codes are returned.
- Keep timeline, dependency, and detail-batch flows on the same compatibility behavior and diagnostics path.
- Require partial error diagnostics to include query mode, endpoint attempted, status code, and upstream error payload details.
- Keep environment-driven runtime inputs and improve placeholder/empty input validation warnings at startup.
- Replace unconditional global urllib3 warning suppression with explicit environment-controlled policy.
- Add environment-aware guardrails so insecure warning suppression is discouraged or blocked in production-like modes unless explicitly overridden.
- Preserve deterministic top-level output contracts and compact phase-tagged error reporting.

## Capabilities

### New Capabilities
- jira-search-compat-and-tls-policy: Ensure robust Jira search compatibility fallback, secure TLS warning policy control, and clear runtime input diagnostics for Atlassian extraction flows.

### Modified Capabilities
- None.

## Impact

- Affected code: services.py search helper, TLS warning policy setup, runtime input handling, and partial error formatting.
- Affected APIs: Jira search endpoints (/rest/api/3/search/jql and /rest/api/3/search), Confluence page lookup.
- Dependencies: Continue using requests/python-dotenv and urllib3 from requests stack.
- Security and operations: Improves observability of insecure transport mode and prevents silent suppression in production-like environments.
