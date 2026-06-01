## 1. Batch-safe ticket detail retrieval

- [x] 1.1 Add configurable ticket detail batch size constant/environment setting.
- [x] 1.2 Implement chunking utility for discovered ticket keys.
- [x] 1.3 Refactor ticket detail lookup to execute batched Jira searches and merge normalized results.
- [x] 1.4 Add partial-error capture per failed batch and preserve successful batch output.

## 2. Jira search compatibility hardening

- [x] 2.1 Refactor Jira search helper to use one tenant-compatible request strategy for timeline, dependency, and detail fetch flows.
- [x] 2.2 Add compatibility diagnostics (endpoint/method/query mode) when HTTP 410 or similar compatibility failures occur.
- [x] 2.3 Validate timeline and dependency queries using the refactored search helper path.

## 3. Runtime input and safety improvements

- [x] 3.1 Move main runtime inputs (Confluence page ID, timeline JQL, dependency JQL, board links) to environment-driven configuration.
- [x] 3.2 Add startup validation and warning messages for placeholder/demo values.
- [x] 3.3 Keep TLS verify-on by default and add explicit runtime warning when insecure override is active.

## 4. Output contract and observability

- [x] 4.1 Ensure deterministic top-level keys remain present across success and failure states.
- [x] 4.2 Add compact phase-tagged partial error entries (input validation, board discovery, detail fetch, query compatibility).
- [x] 4.3 Keep runtime summary counts aligned with discovered/resolved/error totals after batching.

## 5. Verification

- [x] 5.1 Validate large-board scenario where discovered keys exceed single-request limits (no 414).
- [x] 5.2 Validate compatibility scenario for timeline/dependency search and confirm actionable diagnostics on failure.
- [x] 5.3 Validate secure/insecure TLS mode messaging and runtime input quality warnings.
