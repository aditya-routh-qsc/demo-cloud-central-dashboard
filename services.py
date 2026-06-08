"""Focused Jira Kanban extraction service.

Primary flow:
1. Accept one or more Jira Kanban board links.
2. Discover ticket keys from each board.
3. Fetch normalized ticket details for discovered keys.

The module is intentionally procedural/functional and environment-driven.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
import urllib3
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from config_utils import get_database_path

urllib3.disable_warnings()

load_dotenv(override=True)

ATLASSIAN_URL: str = os.getenv("ATLASSIAN_URL", "").rstrip("/")
ATLASSIAN_EMAIL: str = os.getenv("ATLASSIAN_EMAIL", "")
ATLASSIAN_TOKEN: str = os.getenv("ATLASSIAN_TOKEN", "")

DEFAULT_TIMEOUT_SECONDS: float = 10.0
DEFAULT_PAGE_SIZE: int = 50
DEFAULT_RUNTIME_ENVIRONMENT: str = "local"
DEFAULT_MAX_TICKET_FETCH_COUNT: int = 1500
DEFAULT_TICKET_FETCH_WORKERS: int = 8
DEFAULT_RETRY_ATTEMPTS: int = 3
DEFAULT_RETRY_BACKOFF_FACTOR: float = 0.5
DEFAULT_JIRA_SEARCH_PATH: str = "/rest/api/3/search/jql"

_HTTP_SESSION: requests.Session | None = None
_HTTP_SESSION_LOCK: Lock = Lock()

KANBAN_BOARD_PATTERNS: list[str] = [
    r"^/jira/software/c/projects/[^/]+/boards/(?P<board_id>\d+)",
    r"^/jira/boards/(?P<board_id>\d+)",
]


def _is_truthy(raw_value: str) -> bool:
    """Return True for common truthy string values."""
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_timeout_seconds() -> float:
    """Return request timeout in seconds from env, with safe fallback."""
    raw_timeout = os.getenv("ATLASSIAN_TIMEOUT_SECONDS", "").strip()
    if not raw_timeout:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw_timeout)
        return value if value > 0 else DEFAULT_TIMEOUT_SECONDS
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _get_verify_tls() -> bool:
    """Return whether TLS certificates should be verified."""
    raw_value = os.getenv("ATLASSIAN_VERIFY_TLS", "true").strip().lower()
    return raw_value not in {"false", "0", "no", "off"}


def _get_max_ticket_fetch_count() -> int:
    """Return max number of ticket details to fetch per board.

    Set ATLASSIAN_MAX_TICKET_FETCH_COUNT=0 to disable the cap.
    """
    raw_value = os.getenv("ATLASSIAN_MAX_TICKET_FETCH_COUNT", "").strip()
    if not raw_value:
        return DEFAULT_MAX_TICKET_FETCH_COUNT
    try:
        parsed = int(raw_value)
    except ValueError:
        return DEFAULT_MAX_TICKET_FETCH_COUNT
    return parsed if parsed >= 0 else DEFAULT_MAX_TICKET_FETCH_COUNT


def _get_ticket_fetch_workers() -> int:
    """Return worker count for concurrent ticket detail fetches.

    Set ATLASSIAN_TICKET_FETCH_WORKERS to tune throughput.
    """
    raw_value = os.getenv("ATLASSIAN_TICKET_FETCH_WORKERS", "").strip()
    if not raw_value:
        return DEFAULT_TICKET_FETCH_WORKERS
    try:
        parsed = int(raw_value)
    except ValueError:
        return DEFAULT_TICKET_FETCH_WORKERS
    if parsed <= 0:
        return DEFAULT_TICKET_FETCH_WORKERS
    return min(parsed, 32)


def _get_board_jql() -> str:
    """Return optional board JQL filter from environment."""
    return os.getenv("ATLASSIAN_BOARD_JQL", "").strip()


def _get_board_order_by() -> str:
    """Return optional ORDER BY clause fragment for board JQL."""
    return os.getenv("ATLASSIAN_BOARD_ORDER_BY", "").strip()


def _get_jira_search_path() -> str:
    """Return Jira search path with safe default for modern cloud tenants."""
    raw_path = os.getenv("ATLASSIAN_JIRA_SEARCH_PATH", "").strip() or DEFAULT_JIRA_SEARCH_PATH
    if not raw_path.startswith("/"):
        return f"/{raw_path}"
    return raw_path


def _get_allowed_host_aliases() -> set[str]:
    """Return normalized host aliases that are treated as same-tenant."""
    raw_value = os.getenv("ATLASSIAN_ALLOWED_HOST_ALIASES", "")
    aliases = [item.strip() for item in re.split(r"[,\n]", raw_value) if item.strip()]
    return {_normalize_host_alias(item) for item in aliases}


def _get_retry_attempts() -> int:
    """Return retry attempt count for transient Jira GET failures."""
    raw_value = os.getenv("ATLASSIAN_RETRY_ATTEMPTS", "").strip()
    if not raw_value:
        return DEFAULT_RETRY_ATTEMPTS
    try:
        parsed = int(raw_value)
    except ValueError:
        return DEFAULT_RETRY_ATTEMPTS
    return min(max(parsed, 0), 10)


def _get_retry_backoff_factor() -> float:
    """Return retry backoff factor for transient Jira GET failures."""
    raw_value = os.getenv("ATLASSIAN_RETRY_BACKOFF_FACTOR", "").strip()
    if not raw_value:
        return DEFAULT_RETRY_BACKOFF_FACTOR
    try:
        parsed = float(raw_value)
    except ValueError:
        return DEFAULT_RETRY_BACKOFF_FACTOR
    if parsed < 0:
        return DEFAULT_RETRY_BACKOFF_FACTOR
    return min(parsed, 10.0)


def _safe_int(value: Any, default: int | None = None) -> int | None:
    """Convert value to int with fallback default for malformed values."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_host_alias(raw_host: str) -> str:
    """Normalize host text into canonical host[:port] form."""
    candidate = raw_host.strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    return _canonical_host(parsed)


def _canonical_host(parsed: Any) -> str:
    """Return lowercase canonical host representation with non-default port."""
    hostname = (getattr(parsed, "hostname", "") or "").lower()
    if not hostname:
        return ""

    port = getattr(parsed, "port", None)
    scheme = (getattr(parsed, "scheme", "") or "").lower()
    if port is None:
        return hostname

    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        return hostname

    return f"{hostname}:{port}"


def _create_http_session() -> requests.Session:
    """Create shared HTTP session configured for transient retry behavior."""
    session = requests.Session()
    retry_attempts = _get_retry_attempts()
    retry = Retry(
        total=retry_attempts,
        connect=retry_attempts,
        read=retry_attempts,
        status=retry_attempts,
        backoff_factor=_get_retry_backoff_factor(),
        status_forcelist=[429, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_http_session() -> requests.Session:
    """Return shared session instance used by Jira GET requests."""
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        with _HTTP_SESSION_LOCK:
            if _HTTP_SESSION is None:
                _HTTP_SESSION = _create_http_session()
    return _HTTP_SESSION


def _jira_get(
    endpoint: str,
    auth: HTTPBasicAuth,
    params: dict[str, Any],
    timeout_seconds: float,
    verify_tls: bool,
) -> requests.Response:
    """Execute Jira GET through shared session with retry-enabled adapter."""
    session = _get_http_session()
    response = session.get(
        endpoint,
        auth=auth,
        headers={"Accept": "application/json"},
        params=params,
        timeout=timeout_seconds,
        verify=verify_tls,
    )
    response.raise_for_status()
    return response


def _build_board_jql() -> str:
    """Build effective board JQL from base filter and ordering options."""
    jql = _get_board_jql()
    order_by = _get_board_order_by()

    if not jql:
        return ""

    if order_by and "order by" not in jql.lower():
        return f"{jql} ORDER BY {order_by}"

    return jql


def _extract_project_key_from_link(board_link: str) -> str:
    """Extract project key from board link when present."""
    path = urlparse(board_link).path
    match = re.search(r"/projects/(?P<project_key>[A-Z][A-Z0-9_]*)/boards/\d+", path)
    if not match:
        return ""
    return (match.group("project_key") or "").strip().upper()


def _build_discovery_jql(board_link: str) -> str:
    """Build discovery JQL used to find ticket keys before detail fetch."""
    configured_jql = _build_board_jql()
    if configured_jql:
        return configured_jql

    project_key = _extract_project_key_from_link(board_link)
    if not project_key:
        return ""

    order_by = _get_board_order_by()
    base_jql = f"project = {project_key}"
    if order_by and "order by" not in base_jql.lower():
        return f"{base_jql} ORDER BY {order_by}"
    return base_jql


def _get_runtime_environment_mode() -> str:
    """Return normalized runtime environment mode."""
    env_value = os.getenv("ATLASSIAN_ENV", "").strip() or os.getenv("APP_ENV", "").strip()
    return env_value.lower() or DEFAULT_RUNTIME_ENVIRONMENT


def _process_jira_query(
    query_name: str,
    **kwargs: Any,
) -> dict[str, Any] | list[dict[str, Any]] | list[str]:
    """Process Jira API queries through one extensible entry point.

    Supported query_name values:
    - board_ticket_keys
    - search_ticket_keys
    - issue_detail

    Template for adding more queries:
    1. Add a new `elif query_name == "<your_query_name>":` block.
    2. Build endpoint/params/headers there.
    3. Execute request and return parsed result shape.
    """
    auth = _get_auth()
    timeout_seconds = _get_timeout_seconds()
    verify_tls = _get_verify_tls()

    if query_name == "board_ticket_keys":
        board_id = str(kwargs.get("board_id", "")).strip()
        if not board_id:
            raise ValueError("board_ticket_keys query requires board_id")

        endpoint = f"{ATLASSIAN_URL}/rest/agile/1.0/board/{board_id}/issue"
        issue_keys: list[str] = []
        seen_keys: set[str] = set()
        start_at = 0
        jql_filter = _build_board_jql()

        while True:
            params: dict[str, Any] = {
                "fields": "key",
                "startAt": start_at,
                "maxResults": DEFAULT_PAGE_SIZE,
            }
            if jql_filter:
                params["jql"] = jql_filter

            response = _jira_get(
                endpoint=endpoint,
                auth=auth,
                params=params,
                timeout_seconds=timeout_seconds,
                verify_tls=verify_tls,
            )
            payload = response.json()

            issues = payload.get("issues", [])
            for issue in issues:
                issue_key = issue.get("key")
                if issue_key and issue_key not in seen_keys:
                    seen_keys.add(issue_key)
                    issue_keys.append(issue_key)

            total = _safe_int(payload.get("total"), None)
            is_last = bool(payload.get("isLast", False))
            start_at += len(issues)
            if is_last or not issues or (total is not None and start_at >= total):
                break

        return issue_keys

    if query_name == "search_ticket_keys":
        jql = str(kwargs.get("jql", "")).strip()
        if not jql:
            raise ValueError("search_ticket_keys query requires jql")

        endpoint = f"{ATLASSIAN_URL}{_get_jira_search_path()}"
        issue_keys: list[str] = []
        seen_keys: set[str] = set()
        start_at = 0
        next_page_token = ""

        while True:
            params: dict[str, Any] = {
                "fields": "key",
                "maxResults": DEFAULT_PAGE_SIZE,
                "jql": jql,
            }
            if next_page_token:
                params["nextPageToken"] = next_page_token
            else:
                params["startAt"] = start_at

            response = _jira_get(
                endpoint=endpoint,
                auth=auth,
                params=params,
                timeout_seconds=timeout_seconds,
                verify_tls=verify_tls,
            )
            payload = response.json()

            issues = payload.get("issues", [])
            for issue in issues:
                issue_key = issue.get("key")
                if issue_key and issue_key not in seen_keys:
                    seen_keys.add(issue_key)
                    issue_keys.append(issue_key)

            next_page_token = str(payload.get("nextPageToken", "") or "").strip()
            is_last = bool(payload.get("isLast", False))
            total = _safe_int(payload.get("total"), None)
            start_at += len(issues)

            if next_page_token:
                continue
            if is_last or not issues or (total is not None and start_at >= total):
                break

        return issue_keys

    if query_name == "issue_detail":
        issue_key = str(kwargs.get("issue_key", "")).strip()
        fields = kwargs.get("fields", [])

        if not issue_key:
            raise ValueError("issue_detail query requires issue_key")
        if not isinstance(fields, list) or not fields:
            raise ValueError("issue_detail query requires fields list")

        endpoint = f"{ATLASSIAN_URL}/rest/api/3/issue/{issue_key}"
        response = _jira_get(
            endpoint=endpoint,
            auth=auth,
            params={"fields": ",".join(fields)},
            timeout_seconds=timeout_seconds,
            verify_tls=verify_tls,
        )
        issue = response.json()

        issue_fields = issue.get("fields", {})
        assignee = issue_fields.get("assignee") or {}
        priority = issue_fields.get("priority") or {}
        issue_type = issue_fields.get("issuetype") or {}
        status = issue_fields.get("status") or {}
        reporter = issue_fields.get("reporter") or {}
        story_points = (
            issue_fields.get("customfield_10006")
            if issue_fields.get("customfield_10006") is not None
            else issue_fields.get("customfield_10016")
        )

        return {
            "ticket_key": issue.get("key", issue_key),
            "summary": issue_fields.get("summary", ""),
            "status": status.get("name", ""),
            "assignee": assignee.get("displayName", "Unassigned") if isinstance(assignee, dict) else "Unassigned",
            "priority": priority.get("name", ""),
            "issue_type": issue_type.get("name", ""),
            "updated": issue_fields.get("updated", ""),
            "issuelinks": issue_fields.get("issuelinks", []),
            "reporter": reporter.get("displayName", "Unassigned") if isinstance(reporter, dict) else "Unassigned",
            "report_date": issue_fields.get("created", ""),
            "due_date": issue_fields.get("duedate"),
            "story_points": story_points,
            "resolution_date": issue_fields.get("resolutiondate"),
            "time_original_estimate": issue_fields.get("timeoriginalestimate"),
            "time_estimate": issue_fields.get("timeestimate"),
            "time_spent": issue_fields.get("timespent"),
        }

    raise ValueError(f"Unsupported query_name: {query_name}")


def _build_tls_warning_policy_status() -> dict[str, Any]:
    """Return warning suppression policy decision and optional warning text."""
    return _build_tls_warning_policy_status_with_inputs(
        verify_tls=_get_verify_tls(),
        env_mode=_get_runtime_environment_mode(),
        suppression_requested=_is_truthy(
            os.getenv("ATLASSIAN_SUPPRESS_INSECURE_TLS_WARNING", "false")
        ),
        override_in_prod=_is_truthy(
            os.getenv("ATLASSIAN_ALLOW_INSECURE_TLS_WARNING_SUPPRESSION_IN_PROD", "false")
        ),
    )


def _build_tls_warning_policy_status_with_inputs(
    verify_tls: bool,
    env_mode: str,
    suppression_requested: bool,
    override_in_prod: bool,
) -> dict[str, Any]:
    """Build TLS warning suppression policy from explicit inputs."""
    normalized_env_mode = env_mode.lower().strip() or DEFAULT_RUNTIME_ENVIRONMENT

    status: dict[str, Any] = {
        "environment_mode": normalized_env_mode,
        "verify_tls": verify_tls,
        "suppression_mode": "disabled",
        "suppression_enabled": False,
        "warning": "",
    }

    if not suppression_requested:
        return status

    if verify_tls:
        status["suppression_mode"] = "not-needed"
        status["warning"] = (
            "[security] TLS warning suppression requested but ATLASSIAN_VERIFY_TLS=true; "
            "suppression not applied."
        )
        return status

    if normalized_env_mode in {"prod", "production", "staging"} and not override_in_prod:
        status["suppression_mode"] = "blocked-by-policy"
        status["warning"] = (
            "[security] TLS warning suppression blocked in production-like mode. "
            "Set ATLASSIAN_ALLOW_INSECURE_TLS_WARNING_SUPPRESSION_IN_PROD=true to override."
        )
        return status

    status["suppression_mode"] = "enabled"
    status["suppression_enabled"] = True
    return status


def _apply_tls_warning_suppression_policy() -> dict[str, Any]:
    """Apply TLS warning suppression policy and return policy status."""
    policy = _build_tls_warning_policy_status()
    if policy["suppression_enabled"]:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return policy


def _get_auth() -> HTTPBasicAuth:
    """Build HTTP basic auth for Atlassian API calls."""
    missing: list[str] = []
    if not ATLASSIAN_URL:
        missing.append("ATLASSIAN_URL")
    if not ATLASSIAN_EMAIL:
        missing.append("ATLASSIAN_EMAIL")
    if not ATLASSIAN_TOKEN:
        missing.append("ATLASSIAN_TOKEN")
    if missing:
        raise ValueError("Missing required Atlassian configuration: " + ", ".join(missing))
    return HTTPBasicAuth(ATLASSIAN_EMAIL, ATLASSIAN_TOKEN)


def _normalize_kanban_links(kanban_links: str | list[str]) -> list[str]:
    """Normalize Kanban input into a clean list of links."""
    if isinstance(kanban_links, str):
        split_links = re.split(r"[,\n]", kanban_links)
    else:
        split_links = list(kanban_links)
    return [link.strip() for link in split_links if link.strip()]


def _extract_board_id_from_link(board_link: str) -> str | None:
    """Extract Jira board ID from supported link patterns."""
    path = urlparse(board_link).path
    for pattern in KANBAN_BOARD_PATTERNS:
        match = re.match(pattern, path)
        if match:
            return match.group("board_id")
    return None


def _validate_kanban_link(board_link: str) -> tuple[bool, str | None, str | None]:
    """Validate Kanban link and return board id when valid."""
    parsed = urlparse(board_link)
    if parsed.scheme not in {"http", "https"}:
        return False, None, "unsupported scheme (expected http/https)"
    if not parsed.netloc:
        return False, None, "missing host"

    if ATLASSIAN_URL:
        expected_host = _canonical_host(urlparse(ATLASSIAN_URL))
        parsed_host = _canonical_host(parsed)
        allowed_hosts = {expected_host}
        allowed_hosts.update(_get_allowed_host_aliases())

        if expected_host and parsed_host not in allowed_hosts:
            allowed_preview = ", ".join(sorted(host for host in allowed_hosts if host))
            return False, None, f"host does not match allowed Atlassian hosts ({allowed_preview})"

    board_id = _extract_board_id_from_link(board_link)
    if not board_id:
        return False, None, "unsupported board URL format"

    return True, board_id, None


def _fetch_board_ticket_keys(board_id: str) -> list[str]:
    """Fetch all issue keys from a Jira board using Agile API pagination."""
    issue_keys = _process_jira_query("board_ticket_keys", board_id=board_id)
    return [str(key) for key in issue_keys]


def _fetch_search_ticket_keys(jql: str) -> list[str]:
    """Fetch all issue keys via Jira search API pagination."""
    issue_keys = _process_jira_query("search_ticket_keys", jql=jql)
    return [str(key) for key in issue_keys]


def _fetch_discovery_ticket_keys(board_id: str, board_link: str) -> tuple[list[str], str, str]:
    """Fetch ticket keys using search JQL when possible, with board fallback."""
    jql = _build_discovery_jql(board_link)
    if jql:
        try:
            return _fetch_search_ticket_keys(jql), "search", jql
        except (requests.RequestException, ValueError):
            # Fall back to board discovery for resilience if search endpoint or query fails.
            pass

    return _fetch_board_ticket_keys(board_id), "board", jql


def _fetch_issue_detail(issue_key: str, fields: list[str]) -> dict[str, Any]:
    """Fetch one Jira issue and normalize its output shape."""
    ticket = _process_jira_query("issue_detail", issue_key=issue_key, fields=fields)
    if not isinstance(ticket, dict):
        raise ValueError("issue_detail query returned invalid payload")
    return ticket


def _fetch_ticket_details_concurrently(
    ticket_keys: list[str],
    fields: list[str],
    board_link: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Fetch ticket details concurrently and return results plus compact errors."""
    if not ticket_keys:
        return [], []

    workers = min(_get_ticket_fetch_workers(), len(ticket_keys))
    results: list[dict[str, Any]] = []
    partial_errors: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_fetch_issue_detail, ticket_key, fields): ticket_key
            for ticket_key in ticket_keys
        }
        for future in as_completed(future_map):
            ticket_key = future_map[future]
            try:
                ticket = future.result()
                ticket["source_links"] = [board_link]
                results.append(ticket)
            except (requests.RequestException, ValueError) as exc:
                partial_errors.append(
                    f"[detail-fetch] failed for ticket '{ticket_key}': {exc}"
                )

    # Keep deterministic order in final output.
    results.sort(key=lambda ticket: ticket.get("ticket_key", ""))
    return results, partial_errors


def parse_issue_dependencies(ticket_key: str, issuelinks: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse raw Jira issue links into classified dependencies and blockers.

    Args:
        ticket_key: The key of the ticket being parsed (e.g., QSYSCLOUD-123).
        issuelinks: Raw Jira issuelinks field content.

    Returns:
        A dictionary containing lists of classified dependency dictionaries:
        - blockers: dependencies that block this ticket (inward block)
        - blocking: issues that this ticket blocks (outward block)
        - other_dependencies: other relations (relates, duplicate, etc.)
    """
    current_project = ticket_key.split("-")[0] if "-" in ticket_key else ""

    blockers = []
    blocking = []
    other_dependencies = []

    if not isinstance(issuelinks, list):
        issuelinks = []

    for link in issuelinks:
        if not isinstance(link, dict):
            continue

        link_type = link.get("type", {})
        if not isinstance(link_type, dict):
            link_type = {}
        link_name = link_type.get("name", "")

        target_issue = None
        direction = None
        relation_desc = ""

        if "inwardIssue" in link:
            target_issue = link.get("inwardIssue")
            direction = "inward"
            relation_desc = link_type.get("inward", "")
        elif "outwardIssue" in link:
            target_issue = link.get("outwardIssue")
            direction = "outward"
            relation_desc = link_type.get("outward", "")

        if not isinstance(target_issue, dict):
            continue

        target_key = target_issue.get("key", "")
        target_project = target_key.split("-")[0] if "-" in target_key else ""

        # Classify as intra_team or inter_team
        is_intra = False
        if current_project and target_project:
            is_intra = current_project.upper() == target_project.upper()
        classification = "intra_team" if is_intra else "inter_team"

        # Get extra fields if present
        target_fields = target_issue.get("fields", {})
        if not isinstance(target_fields, dict):
            target_fields = {}
        target_summary = target_fields.get("summary", "")
        target_status = ""
        if isinstance(target_fields.get("status"), dict):
            target_status = target_fields["status"].get("name", "")

        dep_detail = {
            "ticket_key": target_key,
            "relation_name": link_name,
            "relation_description": relation_desc,
            "direction": direction,
            "classification": classification,
            "summary": target_summary,
            "status": target_status,
        }

        # Identify blockers and blocking
        is_blocker = False
        is_blocking = False

        link_name_lower = link_name.lower()
        relation_desc_lower = relation_desc.lower()

        # Typical blocking indicators:
        if "blocked" in relation_desc_lower or "blocker" in relation_desc_lower or (link_name_lower == "blocks" and direction == "inward"):
            is_blocker = True
        elif "blocks" in relation_desc_lower or (link_name_lower == "blocks" and direction == "outward"):
            is_blocking = True

        if is_blocker:
            blockers.append(dep_detail)
        elif is_blocking:
            blocking.append(dep_detail)
        else:
            other_dependencies.append(dep_detail)

    return {
        "blockers": blockers,
        "blocking": blocking,
        "other_dependencies": other_dependencies,
    }


def find_and_analyze_dependencies(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze dependencies across a list of tickets, summarizing counts and structures.

    Args:
        tickets: List of ticket dictionaries.

    Returns:
        A dictionary with dependency analysis metrics and categorized issues.
    """
    total_dependencies = 0
    blockers_count = 0
    blocking_count = 0
    intra_team_count = 0
    inter_team_count = 0

    all_blockers = []
    all_blocking = []
    all_other_dependencies = []

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        ticket_key = ticket.get("ticket_key", "")
        deps = ticket.get("dependencies", {})
        if not isinstance(deps, dict):
            deps = {}

        ticket_blockers = deps.get("blockers", []) if isinstance(deps.get("blockers", []), list) else []
        ticket_blocking = deps.get("blocking", []) if isinstance(deps.get("blocking", []), list) else []
        ticket_other = deps.get("other_dependencies", []) if isinstance(deps.get("other_dependencies", []), list) else []

        blockers_count += len(ticket_blockers)
        blocking_count += len(ticket_blocking)

        for dep in ticket_blockers:
            if not isinstance(dep, dict):
                continue
            target_ticket = str(dep.get("ticket_key", "")).strip()
            if not target_ticket:
                continue
            if dep.get("classification") == "intra_team":
                intra_team_count += 1
            else:
                inter_team_count += 1

            all_blockers.append({
                "source_ticket": ticket_key,
                "target_ticket": target_ticket,
                "relation": dep.get("relation_description", ""),
                "classification": dep.get("classification", "inter_team"),
                "summary": dep.get("summary", ""),
                "status": dep.get("status", ""),
            })

        for dep in ticket_blocking:
            if not isinstance(dep, dict):
                continue
            target_ticket = str(dep.get("ticket_key", "")).strip()
            if not target_ticket:
                continue
            if dep.get("classification") == "intra_team":
                intra_team_count += 1
            else:
                inter_team_count += 1

            all_blocking.append({
                "source_ticket": ticket_key,
                "target_ticket": target_ticket,
                "relation": dep.get("relation_description", ""),
                "classification": dep.get("classification", "inter_team"),
                "summary": dep.get("summary", ""),
                "status": dep.get("status", ""),
            })

        for dep in ticket_other:
            if not isinstance(dep, dict):
                continue
            target_ticket = str(dep.get("ticket_key", "")).strip()
            if not target_ticket:
                continue
            if dep.get("classification") == "intra_team":
                intra_team_count += 1
            else:
                inter_team_count += 1

            all_other_dependencies.append({
                "source_ticket": ticket_key,
                "target_ticket": target_ticket,
                "relation": dep.get("relation_description", ""),
                "classification": dep.get("classification", "inter_team"),
                "summary": dep.get("summary", ""),
                "status": dep.get("status", ""),
            })

        total_dependencies += len(ticket_blockers) + len(ticket_blocking) + len(ticket_other)

    return {
        "total_dependencies_count": total_dependencies,
        "blockers_count": blockers_count,
        "blocking_count": blocking_count,
        "intra_team_count": intra_team_count,
        "inter_team_count": inter_team_count,
        "details": {
            "blockers": all_blockers,
            "blocking": all_blocking,
            "other_dependencies": all_other_dependencies,
        }
    }


def _upsert_ticket_result(
    tickets_by_key: dict[str, dict[str, Any]],
    incoming_ticket: dict[str, Any],
) -> None:
    """Upsert ticket by key and merge source_links for multi-board membership."""
    ticket_key = str(incoming_ticket.get("ticket_key", "")).strip()
    if not ticket_key:
        return

    incoming_links_raw = incoming_ticket.get("source_links", [])
    incoming_links = (
        [str(link).strip() for link in incoming_links_raw if str(link).strip()]
        if isinstance(incoming_links_raw, list)
        else []
    )

    existing_ticket = tickets_by_key.get(ticket_key)
    if existing_ticket is None:
        new_ticket = dict(incoming_ticket)
        new_ticket["source_links"] = sorted(set(incoming_links))
        tickets_by_key[ticket_key] = new_ticket
        return

    merged_links = set(existing_ticket.get("source_links", []))
    merged_links.update(incoming_links)
    existing_ticket["source_links"] = sorted(link for link in merged_links if link)

    # Fill empty values from incoming record without overriding existing populated data.
    for key, value in incoming_ticket.items():
        if key == "source_links":
            continue
        existing_value = existing_ticket.get(key)
        if existing_value in (None, "", []):
            existing_ticket[key] = value


def _verify_tls_policy_guardrails() -> list[str]:
    """Verify TLS policy enforces production-like suppression guardrails."""
    warnings: list[str] = []
    blocked_policy = _build_tls_warning_policy_status_with_inputs(
        verify_tls=False,
        env_mode="production",
        suppression_requested=True,
        override_in_prod=False,
    )
    if blocked_policy.get("suppression_mode") != "blocked-by-policy" or blocked_policy.get(
        "suppression_enabled"
    ):
        warnings.append(
            "[security] TLS suppression guardrail verification failed for production-like mode."
        )
    return warnings


def get_ticket_details_from_kanban_links(kanban_links: str | list[str]) -> dict[str, Any]:
    """Resolve Kanban links and return normalized ticket details."""
    normalized_links = _normalize_kanban_links(kanban_links)
    fields = [
        "summary", "status", "assignee", "priority", "issuetype", "updated", "issuelinks",
        "reporter", "created", "duedate", "customfield_10006", "customfield_10016",
        "timeoriginalestimate", "timeestimate", "timespent", "resolutiondate"
    ]

    result: dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "input_links": normalized_links,
        "processed_links": [],
        "results": [],
        "unresolved_links": [],
        "partial_errors": [],
    }
    tickets_by_key: dict[str, dict[str, Any]] = {}

    for board_link in normalized_links:
        is_valid, board_id, validation_error = _validate_kanban_link(board_link)
        if not is_valid or not board_id:
            result["unresolved_links"].append(
                {"board_link": board_link, "reason": validation_error}
            )
            result["partial_errors"].append(
                f"[input-validation] invalid board link '{board_link}': {validation_error}"
            )
            continue

        try:
            ticket_keys, discovery_mode, discovery_jql = _fetch_discovery_ticket_keys(board_id, board_link)
            result["processed_links"].append(
                {
                    "board_link": board_link,
                    "board_id": board_id,
                    "discovered_count": len(ticket_keys),
                    "discovery_mode": discovery_mode,
                    "discovery_jql": discovery_jql,
                }
            )
        except (requests.RequestException, ValueError) as exc:
            result["unresolved_links"].append(
                {"board_link": board_link, "board_id": board_id, "reason": str(exc)}
            )
            result["partial_errors"].append(
                f"[board-discovery] failed for board '{board_link}': {exc}"
            )
            continue

        max_ticket_fetch_count = _get_max_ticket_fetch_count()
        selected_ticket_keys = ticket_keys
        if max_ticket_fetch_count > 0:
            selected_ticket_keys = ticket_keys[:max_ticket_fetch_count]
            skipped_count = len(ticket_keys) - len(selected_ticket_keys)
            if skipped_count > 0:
                result["partial_errors"].append(
                    "[detail-fetch] "
                    f"skipped {skipped_count} tickets for board {board_id} due to "
                    f"ATLASSIAN_MAX_TICKET_FETCH_COUNT={max_ticket_fetch_count}."
                )

        board_results, board_errors = _fetch_ticket_details_concurrently(
            selected_ticket_keys,
            fields,
            board_link,
        )

        # Parse dependencies for each ticket
        for ticket in board_results:
            ticket_key = ticket.get("ticket_key", "")
            raw_links = ticket.get("issuelinks", [])
            ticket["dependencies"] = parse_issue_dependencies(ticket_key, raw_links)
            _upsert_ticket_result(tickets_by_key, ticket)

        result["partial_errors"].extend(board_errors)

    result["results"] = sorted(
        tickets_by_key.values(),
        key=lambda ticket: ticket.get("ticket_key", ""),
    )

    # Perform top-level dependency analysis
    dependency_analysis = find_and_analyze_dependencies(result["results"])
    result["dependency_analysis"] = dependency_analysis

    result["counts"] = {
        "links_provided": len(result["input_links"]),
        "links_processed": len(result["processed_links"]),
        "tickets_discovered": sum(
            int(link.get("discovered_count", 0)) for link in result["processed_links"]
        ),
        "tickets_resolved": len(result["results"]),
        "unresolved_links": len(result["unresolved_links"]),
        "errors": len(result["partial_errors"]),
        "total_dependencies": dependency_analysis.get("total_dependencies_count", 0),
        "blockers": dependency_analysis.get("blockers_count", 0),
        "intra_team_dependencies": dependency_analysis.get("intra_team_count", 0),
        "inter_team_dependencies": dependency_analysis.get("inter_team_count", 0),
    }

    return result


def _get_runtime_inputs() -> dict[str, Any]:
    """Read runtime inputs from environment with safe defaults."""
    default_board_link = (
        f"{ATLASSIAN_URL}/jira/software/c/projects/QSYSCLOUD/boards/1863"
        if ATLASSIAN_URL
        else "https://your-company.atlassian.net/jira/software/c/projects/KEY/boards/1"
    )
    raw_links = os.getenv("ATLASSIAN_KANBAN_LINKS", default_board_link)
    return {"kanban_links": _normalize_kanban_links(raw_links)}


def _collect_runtime_warnings(runtime_inputs: dict[str, Any]) -> list[str]:
    """Return runtime warnings for low-quality startup input."""
    warnings: list[str] = []
    if not runtime_inputs.get("kanban_links"):
        warnings.append("[input-validation] ATLASSIAN_KANBAN_LINKS is empty.")
    warnings.extend(_verify_tls_policy_guardrails())
    return warnings


def create_kanban_response_json_file(
    output_file_path: str = "kanban_ticket_details_response.json",
    kanban_links: str | list[str] | None = None,
) -> dict[str, Any]:
    """Fetch Kanban ticket details and save the full response as JSON.

    Args:
        output_file_path: Relative or absolute output JSON file path.
        kanban_links: Optional Kanban links override. When omitted, runtime
            environment inputs are used.

    Returns:
        A dictionary containing the output path, response counts, and full
        response payload.
    """
    resolved_links = (
        _normalize_kanban_links(kanban_links)
        if kanban_links is not None
        else _get_runtime_inputs()["kanban_links"]
    )

    response = get_ticket_details_from_kanban_links(resolved_links)
    absolute_path = os.path.abspath(output_file_path)

    with open(absolute_path, "w", encoding="utf-8") as output_file:
        json.dump(response, output_file, indent=2)

    return {
        "output_path": absolute_path,
        "counts": response.get("counts", {}),
        "response": response,
    }


def _open_sqlite_connection(db_path: str) -> sqlite3.Connection:
    """Open sqlite connection and support URI-based in-memory databases."""
    use_uri = db_path.startswith("file:")
    return sqlite3.connect(db_path, uri=use_uri)


def _to_json_text(value: Any) -> str:
    """Serialize values to compact UTF-8-safe JSON text."""
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _to_bool_int(value: Any) -> int | None:
    """Convert truthy/falsey values into sqlite-friendly integer flags."""
    if value is None:
        return None
    return 1 if bool(value) else 0


def _ensure_sqlite_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    """Add a column if missing so existing DB files can be upgraded in place."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {str(row[1]) for row in rows}
    if column_name in existing_columns:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _init_jira_tables_with_connection(conn: sqlite3.Connection) -> None:
    """Create Jira sync tables if missing."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS teams (
            team_id TEXT PRIMARY KEY,
            display_name TEXT,
            description TEXT,
            cloud_id TEXT,
            organization_id TEXT,
            state TEXT,
            team_type TEXT,
            is_verified INTEGER,
            profile_url TEXT,
            member_count INTEGER,
            includes_you INTEGER,
            team_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT,
            account_id TEXT,
            display_name TEXT,
            email TEXT,
            canonical_account_id TEXT,
            account_status TEXT,
            nickname TEXT,
            picture TEXT,
            zoneinfo TEXT,
            locale TEXT,
            org_id TEXT,
            profile_url TEXT,
            member_role TEXT,
            member_state TEXT,
            member_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE(team_id, account_id)
        );
        """
    )

    # Migration path for older DB files created before expanded Jira sync fields.
    _ensure_sqlite_column(conn, "teams", "organization_id", "organization_id TEXT")
    _ensure_sqlite_column(conn, "teams", "state", "state TEXT")
    _ensure_sqlite_column(conn, "teams", "team_type", "team_type TEXT")
    _ensure_sqlite_column(conn, "teams", "is_verified", "is_verified INTEGER")
    _ensure_sqlite_column(conn, "teams", "profile_url", "profile_url TEXT")
    _ensure_sqlite_column(conn, "teams", "member_count", "member_count INTEGER")
    _ensure_sqlite_column(conn, "teams", "includes_you", "includes_you INTEGER")
    _ensure_sqlite_column(conn, "teams", "team_json", "team_json TEXT NOT NULL DEFAULT '{}' ")
    _ensure_sqlite_column(conn, "teams", "updated_at", "updated_at TEXT NOT NULL DEFAULT ''")

    _ensure_sqlite_column(conn, "team_members", "canonical_account_id", "canonical_account_id TEXT")
    _ensure_sqlite_column(conn, "team_members", "account_status", "account_status TEXT")
    _ensure_sqlite_column(conn, "team_members", "nickname", "nickname TEXT")
    _ensure_sqlite_column(conn, "team_members", "picture", "picture TEXT")
    _ensure_sqlite_column(conn, "team_members", "zoneinfo", "zoneinfo TEXT")
    _ensure_sqlite_column(conn, "team_members", "locale", "locale TEXT")
    _ensure_sqlite_column(conn, "team_members", "org_id", "org_id TEXT")
    _ensure_sqlite_column(conn, "team_members", "profile_url", "profile_url TEXT")
    _ensure_sqlite_column(conn, "team_members", "member_role", "member_role TEXT")
    _ensure_sqlite_column(conn, "team_members", "member_state", "member_state TEXT")
    _ensure_sqlite_column(conn, "team_members", "member_json", "member_json TEXT NOT NULL DEFAULT '{}' ")
    _ensure_sqlite_column(conn, "team_members", "updated_at", "updated_at TEXT NOT NULL DEFAULT ''")


def _extract_team_nodes(teams_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract team nodes list from expected Jira GraphQL response paths."""
    data = teams_data.get("data") if isinstance(teams_data, dict) else None
    if not isinstance(data, dict):
        raise ValueError("Jira GraphQL response missing 'data' object")

    team_roots: list[dict[str, Any]] = []
    for key in ("team", "teams"):
        value = data.get(key)
        if isinstance(value, dict):
            team_roots.append(value)

    # Include data itself to support flat response shapes from gateway variants.
    team_roots.append(data)

    for root in team_roots:
        for key in ("teamSearchV2", "teamSearch", "teams"):
            search_node = root.get(key)
            if isinstance(search_node, dict) and isinstance(search_node.get("nodes"), list):
                nodes_raw = search_node.get("nodes")
                nodes: list[Any] = nodes_raw if isinstance(nodes_raw, list) else []
                extracted: list[dict[str, Any]] = []
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    team_payload = node.get("team")
                    if isinstance(team_payload, dict):
                        merged_team_payload = dict(team_payload)
                        if "memberCount" in node:
                            merged_team_payload["memberCount"] = node.get("memberCount")
                        if "includesYou" in node:
                            merged_team_payload["includesYou"] = node.get("includesYou")
                        extracted.append(merged_team_payload)
                        continue
                    extracted.append(node)
                return extracted
        if isinstance(root.get("nodes"), list):
            nodes_raw = root.get("nodes")
            nodes: list[Any] = nodes_raw if isinstance(nodes_raw, list) else []
            return [node for node in nodes if isinstance(node, dict)]

    raise ValueError("Jira GraphQL response missing teams nodes")


def _extract_member_nodes(team_node: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract member nodes from one team node."""
    members = team_node.get("members")
    if isinstance(members, list):
        return [node for node in members if isinstance(node, dict)]
    if not isinstance(members, dict):
        return []

    nodes = members.get("nodes")
    if isinstance(nodes, list):
        extracted: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            member_payload = node.get("member")
            if isinstance(member_payload, dict):
                merged_member_payload = dict(member_payload)
                if "role" in node:
                    merged_member_payload["memberRole"] = node.get("role")
                if "state" in node:
                    merged_member_payload["memberState"] = node.get("state")
                extracted.append(merged_member_payload)
                continue
            extracted.append(node)
        return extracted

    edges = members.get("edges")
    if isinstance(edges, list):
        extracted: list[dict[str, Any]] = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            node = edge.get("node")
            if isinstance(node, dict):
                extracted.append(node)
        return extracted

    return []


def _resolve_org_ari(domain: str, cloud_id: str, email: str, api_token: str) -> str:
    """Resolve organization ARI needed by teamSearchV2."""
    endpoint = f"https://{domain}/gateway/api/graphql"
    query = """
    query TenantCtx($cloudIds: [ID!]) {
      tenantContexts(cloudIds: $cloudIds) {
        orgId
      }
    }
    """

    response = requests.post(
        endpoint,
        auth=HTTPBasicAuth(email, api_token),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"query": query, "variables": {"cloudIds": [cloud_id]}},
        timeout=_get_timeout_seconds(),
        verify=_get_verify_tls(),
    )
    response.raise_for_status()

    payload = response.json()
    org_id = (
        payload.get("data", {})
        .get("tenantContexts", [{}])[0]
        .get("orgId", "")
        if isinstance(payload, dict)
        else ""
    )
    normalized_org_id = str(org_id).strip()
    if not normalized_org_id:
        return ""

    if normalized_org_id.startswith("ari:"):
        return normalized_org_id
    return f"ari:cloud:platform::org/{normalized_org_id}"


def _build_jira_profile_url(domain: str, account_id: str) -> str:
    """Build a Jira user profile URL from a site domain and account id."""
    normalized_domain = str(domain).strip().replace("https://", "").replace("http://", "").strip("/")
    normalized_account_id = str(account_id).strip()
    if not normalized_domain or not normalized_account_id:
        return ""
    return f"https://{normalized_domain}/jira/people/{normalized_account_id}"


def _enrich_teams_data_with_profile_urls(teams_data: dict[str, Any], domain: str) -> dict[str, Any]:
    """Return a deep-copied teams payload with profile URLs added for each member."""
    if not isinstance(teams_data, dict):
        return teams_data

    enriched = json.loads(json.dumps(teams_data))
    for team_node in _extract_team_nodes(enriched):
        for member_node in _extract_member_nodes(team_node):
            account_id = str(member_node.get("accountId") or member_node.get("id") or "").strip()
            profile_url = _build_jira_profile_url(domain, account_id)
            if profile_url:
                member_node["profile_url"] = profile_url
    return enriched


def init_jira_tables(db_path: str) -> None:
    """Initialize Jira teams and member tracking tables."""
    if not str(db_path).strip():
        raise ValueError("db_path is required")

    with _open_sqlite_connection(db_path) as conn:
        _init_jira_tables_with_connection(conn)
        conn.commit()


def fetch_jira_teams_and_members(
    domain: str,
    email: str,
    api_token: str,
    cloud_id: str,
    tql_query: str,
) -> dict[str, Any]:
    """Fetch Jira teams and nested members using GraphQL gateway."""
    normalized_domain = str(domain).strip().replace("https://", "").replace("http://", "").strip("/")
    if not normalized_domain:
        raise ValueError("domain is required")
    if not str(email).strip():
        raise ValueError("email is required")
    if not str(api_token).strip():
        raise ValueError("api_token is required")
    if not str(cloud_id).strip():
        raise ValueError("cloud_id is required")

    endpoint = f"https://{normalized_domain}/gateway/api/graphql"
    resolved_org_ari = ""
    try:
        resolved_org_ari = _resolve_org_ari(
            domain=normalized_domain,
            cloud_id=cloud_id,
            email=email,
            api_token=api_token,
        )
    except requests.RequestException:
        resolved_org_ari = ""

    query_attempts: list[dict[str, Any]] = [
        {
            "query": """
            query TeamSearchClassic($cloudId: ID!, $tql: String!) {
              team {
                teams(cloudId: $cloudId, first: 100, query: $tql) {
                  nodes {
                    teamId
                    id
                    displayName
                    description
                    members(first: 200) {
                      nodes {
                        member {
                          ... on AtlassianAccountUser {
                            accountId
                            displayName
                            name
                            email
                            emailAddress
                          }
                        }
                        accountId
                        displayName
                        email
                        emailAddress
                      }
                    }
                  }
                }
              }
            }
            """,
            "variables": {
                "cloudId": cloud_id,
                "tql": tql_query,
            },
        },
                {
                        "query": """
                        query TeamSearchV2OrgSite($orgId: ID!, $siteId: String!, $query: String) {
                            team {
                                teamSearchV2(organizationId: $orgId, siteId: $siteId, filter: {query: $query}, first: 100) {
                                    nodes {
                                        team {
                                            id
                                            displayName
                                            description
                                            members(first: 200) {
                                                nodes {
                                                    member {
                                                        ... on AtlassianAccountUser {
                                                            accountId
                                                            name
                                                            email
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        """,
                        "variables": {
                                "orgId": resolved_org_ari,
                                "siteId": cloud_id,
                                "query": tql_query,
                        },
                        "skip": not resolved_org_ari,
                },
        {
            "query": """
            query TeamSearchV2($cloudId: ID!, $tql: String!) {
              team {
                teamSearchV2(cloudId: $cloudId, tql: $tql, first: 100) {
                  nodes {
                    teamId
                    id
                    displayName
                    description
                    members(first: 200) {
                      nodes {
                        accountId
                        displayName
                        email
                        emailAddress
                      }
                    }
                  }
                }
              }
            }
            """,
            "variables": {
                "cloudId": cloud_id,
                "tql": tql_query,
            },
        },
    ]

    errors: list[Any] = []
    for attempt in query_attempts:
        if attempt.get("skip"):
            continue

        response = requests.post(
            endpoint,
            auth=HTTPBasicAuth(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=attempt,
            timeout=_get_timeout_seconds(),
            verify=_get_verify_tls(),
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            errors.append("Jira GraphQL response is not a dictionary")
            continue

        payload_errors = payload.get("errors")
        if payload_errors:
            errors.append(payload_errors)
            continue

        try:
            _extract_team_nodes(payload)
            return payload
        except ValueError as exc:
            errors.append(str(exc))

    raise ValueError(f"Jira GraphQL returned errors: {errors}")


def save_jira_data_to_db(db_path: str, teams_data: dict[str, Any], cloud_id: str) -> dict[str, int]:
    """Persist Jira team/member GraphQL payload into sqlite with upserts."""
    if not str(db_path).strip():
        raise ValueError("db_path is required")
    if not isinstance(teams_data, dict):
        raise ValueError("teams_data must be a dictionary")
    if not str(cloud_id).strip():
        raise ValueError("cloud_id is required")

    team_nodes = _extract_team_nodes(teams_data)
    team_upserts = 0
    member_upserts = 0
    updated_at_iso = datetime.now(timezone.utc).isoformat()
    fallback_domain = _resolve_domain_from_atlassian_url()

    with _open_sqlite_connection(db_path) as conn:
        _init_jira_tables_with_connection(conn)

        for team_node in team_nodes:
            team_id = str(team_node.get("teamId") or team_node.get("id") or "").strip()
            if not team_id:
                continue

            display_name = str(team_node.get("displayName") or "").strip()
            description = str(team_node.get("description") or "").strip()

            conn.execute(
                """
                INSERT INTO teams (
                    team_id, display_name, description, cloud_id,
                    organization_id, state, team_type, is_verified,
                    profile_url, member_count, includes_you, team_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    description=excluded.description,
                    cloud_id=excluded.cloud_id,
                    organization_id=excluded.organization_id,
                    state=excluded.state,
                    team_type=excluded.team_type,
                    is_verified=excluded.is_verified,
                    profile_url=excluded.profile_url,
                    member_count=excluded.member_count,
                    includes_you=excluded.includes_you,
                    team_json=excluded.team_json,
                    updated_at=excluded.updated_at
                """,
                (
                    team_id,
                    display_name,
                    description,
                    cloud_id,
                    str(team_node.get("organizationId") or "").strip(),
                    str(team_node.get("state") or "").strip(),
                    str(team_node.get("type") or "").strip(),
                    _to_bool_int(team_node.get("isVerified")),
                    str(team_node.get("profileUrl") or "").strip(),
                    _safe_int(team_node.get("memberCount"), None),
                    _to_bool_int(team_node.get("includesYou")),
                    _to_json_text(team_node),
                    updated_at_iso,
                ),
            )
            team_upserts += 1

            for member_node in _extract_member_nodes(team_node):
                account_id = str(member_node.get("accountId") or member_node.get("id") or "").strip()
                if not account_id:
                    continue

                member_display_name = str(member_node.get("displayName") or member_node.get("name") or "").strip()
                member_email = str(member_node.get("email") or member_node.get("emailAddress") or "").strip()
                member_profile_url = str(member_node.get("profile_url") or "").strip()
                if not member_profile_url and fallback_domain:
                    member_profile_url = _build_jira_profile_url(fallback_domain, account_id)

                conn.execute(
                    """
                    INSERT INTO team_members (
                        team_id, account_id, display_name, email,
                        canonical_account_id, account_status, nickname, picture,
                        zoneinfo, locale, org_id, profile_url, member_role, member_state,
                        member_json, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(team_id, account_id) DO UPDATE SET
                        display_name=excluded.display_name,
                        email=excluded.email,
                        canonical_account_id=excluded.canonical_account_id,
                        account_status=excluded.account_status,
                        nickname=excluded.nickname,
                        picture=excluded.picture,
                        zoneinfo=excluded.zoneinfo,
                        locale=excluded.locale,
                        org_id=excluded.org_id,
                        profile_url=excluded.profile_url,
                        member_role=excluded.member_role,
                        member_state=excluded.member_state,
                        member_json=excluded.member_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        team_id,
                        account_id,
                        member_display_name,
                        member_email,
                        str(member_node.get("canonicalAccountId") or "").strip(),
                        str(member_node.get("accountStatus") or "").strip(),
                        str(member_node.get("nickname") or "").strip(),
                        str(member_node.get("picture") or "").strip(),
                        str(member_node.get("zoneinfo") or "").strip(),
                        str(member_node.get("locale") or "").strip(),
                        str(member_node.get("orgId") or "").strip(),
                        member_profile_url,
                        str(member_node.get("memberRole") or member_node.get("role") or "").strip(),
                        str(member_node.get("memberState") or member_node.get("state") or "").strip(),
                        _to_json_text(member_node),
                        updated_at_iso,
                    ),
                )
                member_upserts += 1

        conn.commit()

    return {
        "teams_upserted": team_upserts,
        "members_upserted": member_upserts,
    }


def sync_jira_teams_pipeline(
    domain: str,
    email: str,
    api_token: str,
    cloud_id: str,
    tql_query: str,
    db_path: str,
) -> dict[str, int]:
    """Run Jira team synchronization pipeline end-to-end."""
    init_jira_tables(db_path)
    teams_data = fetch_jira_teams_and_members(
        domain=domain,
        email=email,
        api_token=api_token,
        cloud_id=cloud_id,
        tql_query=tql_query,
    )
    enriched_teams_data = _enrich_teams_data_with_profile_urls(teams_data, domain)
    return save_jira_data_to_db(db_path=db_path, teams_data=enriched_teams_data, cloud_id=cloud_id)


def _resolve_domain_from_atlassian_url() -> str:
    """Resolve Atlassian domain from ATLASSIAN_URL or domain environment fallback."""
    parsed = urlparse(ATLASSIAN_URL)
    if parsed.netloc:
        return parsed.netloc
    return os.getenv("ATLASSIAN_DOMAIN", "").strip()


def _resolve_cloud_id(domain: str) -> str:
    """Resolve cloud id from env or Atlassian tenant info endpoint."""
    env_cloud_id = os.getenv("ATLASSIAN_CLOUD_ID", "").strip()
    if env_cloud_id:
        return env_cloud_id

    normalized_domain = str(domain).strip().replace("https://", "").replace("http://", "").strip("/")
    if not normalized_domain:
        return ""

    endpoint = f"https://{normalized_domain}/_edge/tenant_info"
    response = requests.get(
        endpoint,
        headers={"Accept": "application/json"},
        timeout=_get_timeout_seconds(),
        verify=_get_verify_tls(),
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        return ""

    cloud_id = str(payload.get("cloudId") or payload.get("cloud_id") or "").strip()
    return cloud_id


def create_jira_teams_response_json_file(
    output_file_path: str = "jira_teams_and_members_response.json",
    domain: str | None = None,
    email: str | None = None,
    api_token: str | None = None,
    cloud_id: str | None = None,
    tql_query: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Fetch Jira team/member payload, persist it, and save full JSON response to disk."""
    resolved_domain = (domain or _resolve_domain_from_atlassian_url()).strip()
    resolved_email = (email or ATLASSIAN_EMAIL).strip()
    resolved_api_token = (api_token or ATLASSIAN_TOKEN).strip()
    resolved_cloud_id = (cloud_id or _resolve_cloud_id(resolved_domain)).strip()
    resolved_tql_query = (tql_query or os.getenv("ATLASSIAN_TEAM_TQL_QUERY", "")).strip()
    resolved_db_path = (db_path or get_database_path()).strip()

    if not resolved_domain:
        raise ValueError("Missing Jira team sync input: domain")
    if not resolved_email:
        raise ValueError("Missing Jira team sync input: email")
    if not resolved_api_token:
        raise ValueError("Missing Jira team sync input: api_token")
    if not resolved_cloud_id:
        raise ValueError("Missing Jira team sync input: cloud_id")

    teams_data = fetch_jira_teams_and_members(
        domain=resolved_domain,
        email=resolved_email,
        api_token=resolved_api_token,
        cloud_id=resolved_cloud_id,
        tql_query=resolved_tql_query,
    )
    enriched_teams_data = _enrich_teams_data_with_profile_urls(teams_data, resolved_domain)
    sync_counts = save_jira_data_to_db(
        db_path=resolved_db_path,
        teams_data=enriched_teams_data,
        cloud_id=resolved_cloud_id,
    )

    output_payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "domain": resolved_domain,
        "cloud_id": resolved_cloud_id,
        "tql_query": resolved_tql_query,
        "sync_counts": sync_counts,
        "teams_data": enriched_teams_data,
    }

    absolute_path = os.path.abspath(output_file_path)
    with open(absolute_path, "w", encoding="utf-8") as output_file:
        json.dump(output_payload, output_file, indent=2)

    return {
        "output_path": absolute_path,
        "sync_counts": sync_counts,
        "response": output_payload,
    }


if __name__ == "__main__":
    runtime_inputs = _get_runtime_inputs()
    runtime_warnings = _collect_runtime_warnings(runtime_inputs)
    tls_policy = _apply_tls_warning_suppression_policy()

    print(
        "[startup] "
        f"environment={tls_policy.get('environment_mode')}; "
        f"tls_verify={tls_policy.get('verify_tls')}; "
        f"tls_warning_suppression={tls_policy.get('suppression_mode')}; "
        f"kanban_links={len(runtime_inputs.get('kanban_links', []))}"
    )

    if not _get_verify_tls():
        print(
            "[security] TLS certificate verification is disabled "
            "(ATLASSIAN_VERIFY_TLS=false). Use only for local troubleshooting."
        )

    policy_warning = str(tls_policy.get("warning", "")).strip()
    if policy_warning:
        print(policy_warning)

    for warning in runtime_warnings:
        print(warning)

    print("Running Kanban ticket detail extraction...")
    saved = create_kanban_response_json_file(
        output_file_path="outputs/kanban_ticket_details_response.json",
        kanban_links=runtime_inputs["kanban_links"],
    )
    data = saved["response"]
    counts = data.get("counts", {})

    print(f"- Response JSON file: {saved['output_path']}")

    print("\nSummary")
    print(f"- Links provided: {counts.get('links_provided', 0)}")
    print(f"- Links processed: {counts.get('links_processed', 0)}")
    print(f"- Tickets resolved: {counts.get('tickets_resolved', 0)}")
    print(f"- Unresolved links: {counts.get('unresolved_links', 0)}")
    print(f"- Partial errors: {counts.get('errors', 0)}")

    print("\nDependency & Blocker Analysis")
    print(f"- Total Dependencies: {counts.get('total_dependencies', 0)}")
    print(f"- Blockers: {counts.get('blockers', 0)}")
    print(f"- Intra-team Dependencies: {counts.get('intra_team_dependencies', 0)}")
    print(f"- Inter-team Dependencies: {counts.get('inter_team_dependencies', 0)}")

    print("\nFormatted sample snippet")
    print(
        json.dumps(
            {
                "fetched_at": data.get("fetched_at"),
                "counts": counts,
                "sample_result": (data.get("results") or [{}])[0],
                "sample_unresolved_link": (data.get("unresolved_links") or [{}])[0],
                "partial_errors": data.get("partial_errors", [])[:2],
            },
            indent=2,
        )
    )

    print("\nRunning Jira teams and members extraction...")
    try:
        teams_saved = create_jira_teams_response_json_file(
            output_file_path="outputs/jira_teams_and_members_response.json"
        )
        team_counts = teams_saved.get("sync_counts", {}) if isinstance(teams_saved, dict) else {}
        print(f"- Jira teams JSON file: {teams_saved.get('output_path', '')}")
        print(f"- Teams upserted: {team_counts.get('teams_upserted', 0)}")
        print(f"- Members upserted: {team_counts.get('members_upserted', 0)}")
    except (ValueError, requests.RequestException) as exc:
        print(f"[jira-team-sync] skipped: {exc}")
