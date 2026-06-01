## Why

Runtime execution of the current extraction script reveals production-impacting failures: oversized ticket-detail queries, unsupported Jira search request behavior, placeholder defaults causing false negatives, and insecure TLS configuration in active use. This change is needed now to restore reliable data extraction at real board scale and reduce operational risk.

## What Changes

- Add batching requirements for ticket detail retrieval so large discovered ticket sets do not exceed request URL limits.
- Update Jira search strategy requirements to use request shape/endpoints that are accepted in the current tenant environment.
- Define configuration-driven defaults for Confluence page ID, JQL filters, and sample board links to avoid placeholder-driven runtime failures.
- Define strict runtime behavior for invalid sample inputs and production mode separation.
- Strengthen TLS requirements to keep certificate verification enabled by default and document temporary local-only bypass behavior.
- Add explicit observability requirements for partial failures with actionable error messages (404, 410, 414, timeout).

## Capabilities

### New Capabilities
- atlassian-runtime-hardening: Ensure Atlassian extraction remains reliable under large-ticket volumes, tenant-specific API constraints, and secure transport requirements.

### Modified Capabilities
- None.

## Impact

- Affected code: services.py request composition, ticket detail retrieval flow, input/default handling, and runtime summary output.
- Affected APIs: Jira search and board issue retrieval patterns, Confluence page retrieval.
- Dependencies: No new third-party libraries required; continue with requests and python-dotenv.
- Security and operations: TLS verification posture and environment configuration hygiene become explicit, testable requirements.
