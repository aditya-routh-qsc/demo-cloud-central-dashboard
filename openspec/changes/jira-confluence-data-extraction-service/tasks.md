## 1. Configuration and foundations

- [x] 1.1 Create `services.py` with module-level dotenv loading and shared configuration constants.
- [x] 1.2 Implement `_get_auth()` using environment credentials and clear validation errors for missing required values.
- [x] 1.3 Implement timeout resolution from environment with safe fallback default of 10 seconds.

## 2. Atlassian extraction functions

- [x] 2.1 Implement `fetch_team_rosters(page_id: str) -> dict` against Confluence v2 page endpoint with `body-format=storage`.
- [x] 2.2 Implement `fetch_pod_timelines(jql_query: str) -> list[dict]` with fixed Jira field requests and safe day/progress extraction.
- [x] 2.3 Implement `fetch_cross_team_dependencies(jql_query: str) -> list[dict]` with fixed Jira field requests and inward/outward blocker parsing.

## 3. Aggregation and resilience

- [x] 3.1 Implement `get_all_live_atlassian_data(...) -> dict` to run all extraction functions sequentially.
- [x] 3.2 Add metadata fields (`fetched_at`, `partial_errors`) and section-level partial failure handling.
- [x] 3.3 Ensure unified output always contains `teams`, `timelines`, and `dependencies` keys even during partial failures.

## 4. Documentation and usability

- [x] 4.1 Add beginner-focused inline comments for each JSON extraction path and metric conversion rule.
- [x] 4.2 Add comprehensive function docstrings with input/output contracts and fallback behavior.
- [x] 4.3 Implement `if __name__ == "__main__":` usage block with placeholder arguments, concise counts, and formatted sample snippet output.

## 5. Verification

- [x] 5.1 Run the script locally with placeholder or real env values and verify request wiring plus output schema shape.
- [x] 5.2 Validate timeline field fallback behavior for null or missing estimates/times.
- [x] 5.3 Validate dependency parsing behavior for no-link, inward-link, and outward-link Jira issue cases.
