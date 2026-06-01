## Why

The Q-SYS Cloud centralized dashboard needs a reliable Phase 1 extraction layer that can pull live raw data from Jira Cloud and Confluence with predictable contracts and safe credential handling. This is needed now to unblock downstream parsing, analytics, and visualization work while keeping implementation simple for beginner contributors.

## What Changes

- Add a new Python service module (`services.py`) that uses only `requests` and `python-dotenv` to fetch data from Atlassian Jira REST API v3 and Confluence REST API v2.
- Define a procedural/functional API with standalone functions for authentication, team roster retrieval, timeline/progress retrieval, dependency/blocker mapping, and unified aggregation.
- Standardize Jira API queries to always request fixed field lists for timeline and dependency extraction.
- Add environment-configurable timeout support with a safe in-code default of 10 seconds.
- Define partial-failure behavior in the aggregator so one failed upstream call does not crash the full payload.
- Include response metadata (`fetched_at`, `partial_errors`) in unified output for observability.
- Include beginner-focused inline extraction comments and a usage-oriented main execution block that prints concise summary counts plus a formatted sample snippet.

## Capabilities

### New Capabilities
- `atlassian-data-extraction`: Extract live Confluence and Jira data via explicit functional endpoints with secure environment-based auth, normalized output contracts, metadata, and usage-focused documentation.

### Modified Capabilities
- None.

## Impact

- Affected code: New backend service module and related documentation comments in code.
- Affected external APIs: Atlassian Jira Cloud REST API v3 (`/rest/api/3/search`) and Confluence REST API v2 (`/wiki/api/v2/pages/{page_id}`).
- Dependencies: Requires `requests` and `python-dotenv` only.
- Security: Credentials must be loaded from `.env` (`ATLASSIAN_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_TOKEN`) and never hardcoded.
- Operations: Requires outbound HTTPS access to Atlassian Cloud and sane timeout controls to prevent hanging requests.
