# Change Proposal: Extract Ticket Dependencies and Time Metrics

This document outlines the change proposal for extending the Kanban extraction service (`services.py`) to discover ticket dependencies, identify blockers, classify relationships (intra-team vs. inter-team), and extract detailed time/metadata metrics.

---

## 1. Proposal

### ## Why
Jira Kanban boards often have complex blockers and cross-team dependencies that are not visible in standard flat lists or static Confluence reports. In addition, assessing ticket health and timeline risks requires key time metrics (story points, estimates, spent time) and reporter metadata. This change is needed to provide deep dependency graphing and rich time analytics directly from the Kanban extraction pipeline.

### ## What Changes
* **Query API Fields Expansion**:
  * Expand queries to request `"issuelinks"`, `"reporter"`, `"created"`, `"duedate"`, `"resolutiondate"`, `"timeoriginalestimate"`, `"timeestimate"`, `"timespent"`, and custom story points fields (`customfield_10006`, `customfield_10016`).
* **Dependency Classifier**:
  * Implement `parse_issue_dependencies` to interpret Jira link directions (`inward` vs `outward`) and categorize relationships into `blockers`, `blocking`, and `other_dependencies`.
  * Categorize relationships as `intra_team` (same project prefix) or `inter_team` (different project prefixes).
* **Dependency Aggregator**:
  * Implement `find_and_analyze_dependencies` to generate a top-level summary including `total_dependencies_count`, `blockers_count`, `blocking_count`, `intra_team_count`, `inter_team_count`, and exact node-edge link pairs.
* **Orchestration**:
  * Enrich each ticket in `results` with parsed `"dependencies"`.
  * Inject the root `"dependency_analysis"` report and counts into the output payload.
  * Update the direct CLI runner to output dependency analysis metrics.

### ## Capabilities
#### New Capabilities
* **jira-dependency-analysis**: Parses, filters, and structures directional blocker trees and team boundary lines across Kanban board issues.
* **jira-time-metrics-extraction**: Pulls created/due dates, resolution dates, story points, and core time tracking estimates from individual tickets.

#### Modified Capabilities
* **extract-ticket-details-from-kanban-links**: Enhanced to retrieve advanced metadata fields and enrich output schemas in `kanban_ticket_details_response.json`.

### ## Impact
* **Affected code**: `services.py` (updated `_process_jira_query`, `get_ticket_details_from_kanban_links`, and `__main__` runner).
* **Affected output**: `kanban_ticket_details_response.json` (now contains complete nested dependencies, metadata metrics, and aggregate metrics).
* **Security impact**: None. Authenticated endpoints use existing secure environment-based API tokens.
* **Operational impact**: Enables down-stream frontend dashboards to immediately render interactive dependency graphs and metrics charts.

---

## 2. Design

### ## Context
The current Kanban extraction service successfully fetches active issues and standard attributes (assignee, priority, status). However, it lacked native visibility into what was blocking each ticket, who blocked whom, and detailed time-tracking parameters. A structured extraction and parsing logic was required to bridge this gap.

### ## Goals / Non-Goals
**Goals:**
* Extract both inward and outward ticket dependencies.
* Correctly identify blockers vs general relations (e.g. relates to, duplicates).
* Classify dependencies by project boundary prefixes to flag cross-team coordination risks.
* Pull reporter name and all standard/custom time metrics to calculate velocity.
* Maintain complete backwards-compatibility with the existing output format.

**Non-Goals:**
* Developing the interactive HTML5 frontend UI inside `services.py`.
* Storing dependencies in a persistent database.

### ## Decisions
1. **Project-Prefix Partitioning**
   * *Decision*: Use the issue key prefix (the part before the hyphen, e.g. `QSYSCLOUD`) as the team identifier.
   * *Rationale*: Extremely robust and aligns with Jira company/team-managed project standards.
2. **Explicit Blocker Identification**
   * *Decision*: Flag link types containing "blocked" or "blocker" or company-standard "Blocks" type as active blockers.
   * *Rationale*: Avoids misclassifying simple informational relations (like "relates to") as critical progress blockers.
3. **Primary & Secondary Story Points Fields**
   * *Decision*: Fallback from `customfield_10006` to `customfield_10016` when checking story points.
   * *Rationale*: Story points custom field IDs can vary depending on Jira Software project configurations.

### ## Risks / Trade-offs
* *Risk*: Fetching extra fields increases API payload size slightly.
  * *Mitigation*: The Agile API pagination (maxResults=50) and parallel worker threading keep extraction times near-instantaneous.

### ## Migration & Verification Plan
1. Apply code changes using multi-line replacements in `services.py`.
2. Run `.venv\Scripts\python services.py` to invoke the extraction and parse 99 active tickets.
3. Verify that the terminal displays blocker counts and that the resulting `kanban_ticket_details_response.json` maps all parsed time metrics and dependencies.
