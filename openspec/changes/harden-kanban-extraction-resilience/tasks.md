## 1. TLS Policy And Security Signal Handling

- [x] 1.1 Remove unconditional insecure TLS warning suppression at module import time in [services.py](services.py).
- [x] 1.2 Keep TLS warning suppression exclusively behind runtime policy evaluation in [_apply_tls_warning_suppression_policy](services.py).
- [x] 1.3 Add verification that production-like policy mode blocks suppression unless explicit override is enabled.

## 2. Safe Parsing And Validation Hardening

- [x] 2.1 Add safe numeric conversion helper(s) for pagination fields and replace direct int conversion on Jira payload totals.
- [x] 2.2 Harden dependency aggregation paths to use guarded get access and skip malformed dependency entries.
- [x] 2.3 Normalize host comparison logic and add optional alias-host configuration support for board link validation.

## 3. Deduplication And Source Link Merge

- [x] 3.1 Add ticket upsert map keyed by ticket_key during result aggregation across all board links.
- [x] 3.2 Merge source_links for duplicated ticket keys while preserving deterministic output ordering.
- [x] 3.3 Ensure counts and dependency analysis run against deduplicated ticket results.

## 4. Retry And Session Reuse

- [x] 4.1 Introduce shared requests session initialization for Jira API call paths.
- [x] 4.2 Implement transient retry with exponential backoff for HTTP 429, 502, 503, and 504 on GET operations.
- [x] 4.3 Ensure retry exhaustion records one compact partial error per failed operation.

## 5. Validation And Regression Checks

- [x] 5.1 Validate no duplicate ticket records are emitted when one ticket appears in multiple boards.
- [x] 5.2 Validate pagination safety for null/non-numeric total values and malformed dependency records.
- [x] 5.3 Validate retry behavior for recoverable and non-recoverable transient failures and confirm deterministic output counts.
