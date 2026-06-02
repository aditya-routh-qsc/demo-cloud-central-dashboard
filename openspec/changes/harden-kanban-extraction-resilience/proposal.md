## Why

The Jira Kanban extraction flow currently has resilience and safety gaps that can lead to suppressed security signals, duplicate ticket results, fragile parsing, and avoidable transient API failures. Hardening is needed now to improve correctness, stability, and throughput before broader database-backed sync and dashboard usage scales up.

## What Changes

- Remove unconditional global insecure TLS warning suppression and enforce suppression strictly through runtime policy decisions.
- Add result upsert/deduplication by ticket key across multi-board extraction while merging source link provenance.
- Harden dependency analysis parsing by replacing direct dict indexing with guarded access and malformed-item tolerance.
- Harden pagination and numeric parsing to safely handle null and non-numeric upstream payload values.
- Relax/normalize host validation for board links, with optional allowlisted alias support.
- Add retry with exponential backoff for transient HTTP failures (429, 502, 503, 504).
- Use a shared requests session for connection reuse and better request throughput.

## Capabilities

### New Capabilities
- `jira-extraction-resilience-hardening`: Improves request reliability, payload safety, and deduplicated output correctness for Kanban extraction.
- `jira-network-retry-and-connection-reuse`: Adds transient-error retry policy and shared HTTP session behavior for Atlassian API calls.

### Modified Capabilities
- None.

## Impact

- Affected code: [services.py](services.py) request path, board validation, dependency parsing, and result aggregation logic.
- Affected behavior: fewer transient failures, stronger malformed-payload tolerance, deduplicated multi-board ticket results, and policy-compliant TLS warning handling.
- Operational impact: improved extraction success rates and reduced request overhead via connection reuse.
- Security impact: warning suppression becomes policy-controlled rather than globally disabled at import time.
