"""SQLite connector and persistence helpers for dashboard cache."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import urlparse

from config_utils import get_database_path

TRACKED_HISTORY_FIELDS = [
    "status",
    "assignee",
    "due_date",
    "resolution_date",
    "story_points",
    "time_estimate",
    "time_spent",
]

DONE_STATUS_KEYS = {"done", "closed", "resolved"}
IN_PROGRESS_STATUS_KEYS = {"in progress", "in-progress", "in_review", "in review", "testing"}


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield sqlite connection with row access by column name."""
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create all persistence tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_runs (
                run_id TEXT PRIMARY KEY,
                trigger_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                links_provided INTEGER NOT NULL DEFAULT 0,
                links_processed INTEGER NOT NULL DEFAULT 0,
                tickets_discovered INTEGER NOT NULL DEFAULT 0,
                tickets_resolved INTEGER NOT NULL DEFAULT 0,
                unresolved_links INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                error_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS tickets_current (
                ticket_key TEXT PRIMARY KEY,
                project_key TEXT,
                summary TEXT,
                issue_type TEXT,
                status TEXT,
                priority TEXT,
                assignee TEXT,
                reporter TEXT,
                report_date TEXT,
                due_date TEXT,
                resolution_date TEXT,
                updated TEXT,
                story_points REAL,
                time_original_estimate INTEGER,
                time_estimate INTEGER,
                time_spent INTEGER,
                source_links_json TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                last_seen_run_id TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ticket_dependencies_current (
                source_ticket_key TEXT NOT NULL,
                target_ticket_key TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                relation_name TEXT,
                relation_description TEXT,
                direction TEXT,
                classification TEXT,
                source_project_key TEXT,
                target_project_key TEXT,
                target_status TEXT,
                last_seen_run_id TEXT NOT NULL,
                PRIMARY KEY (source_ticket_key, target_ticket_key, dependency_type, relation_name, direction)
            );

            CREATE TABLE IF NOT EXISTS ticket_history_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_key TEXT NOT NULL,
                run_id TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT
            );

            CREATE TABLE IF NOT EXISTS unresolved_link_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                board_link TEXT NOT NULL,
                board_id TEXT,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_runtime_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            );

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

            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets_current(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_assignee ON tickets_current(assignee);
            CREATE INDEX IF NOT EXISTS idx_tickets_updated ON tickets_current(updated);
            CREATE INDEX IF NOT EXISTS idx_deps_source ON ticket_dependencies_current(source_ticket_key);
            CREATE INDEX IF NOT EXISTS idx_deps_target ON ticket_dependencies_current(target_ticket_key);
            CREATE INDEX IF NOT EXISTS idx_history_ticket ON ticket_history_log(ticket_key, changed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_runs_started ON sync_runs(started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
            CREATE INDEX IF NOT EXISTS idx_team_members_display_name ON team_members(display_name);
            CREATE INDEX IF NOT EXISTS idx_team_members_account_id ON team_members(account_id);
            CREATE INDEX IF NOT EXISTS idx_teams_display_name ON teams(display_name);
            """
        )
        conn.commit()


def _to_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _project_key(ticket_key: str) -> str:
    return ticket_key.split("-")[0] if "-" in ticket_key else ""


def _extract_board_id_from_link(board_link: str) -> str:
    path = urlparse(board_link).path
    parts = [part for part in path.split("/") if part]
    if "boards" in parts:
        idx = parts.index("boards")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def _load_existing_tickets(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    rows = conn.execute("SELECT * FROM tickets_current").fetchall()
    return {str(row["ticket_key"]): row for row in rows}


def _insert_ticket_history(
    conn: sqlite3.Connection,
    run_id: str,
    now_iso: str,
    ticket_key: str,
    previous: sqlite3.Row | None,
    current_ticket: dict[str, Any],
) -> None:
    if previous is None:
        conn.execute(
            """
            INSERT INTO ticket_history_log(ticket_key, run_id, changed_at, field_name, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_key, run_id, now_iso, "created", None, current_ticket.get("status", "")),
        )
        return

    for field_name in TRACKED_HISTORY_FIELDS:
        old_value = previous[field_name] if field_name in previous.keys() else None
        new_value = current_ticket.get(field_name)
        if str(old_value) != str(new_value):
            conn.execute(
                """
                INSERT INTO ticket_history_log(ticket_key, run_id, changed_at, field_name, old_value, new_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ticket_key, run_id, now_iso, field_name, str(old_value) if old_value is not None else None, str(new_value) if new_value is not None else None),
            )


def persist_extraction_result(payload: dict[str, Any], trigger_type: str) -> str:
    """Persist extraction payload into SQLite and return generated run id."""
    init_db()
    run_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    counts = payload.get("counts", {}) if isinstance(payload.get("counts"), dict) else {}
    partial_errors = payload.get("partial_errors", []) if isinstance(payload.get("partial_errors"), list) else []

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_runs(
                run_id, trigger_type, started_at, completed_at, status,
                links_provided, links_processed, tickets_discovered, tickets_resolved,
                unresolved_links, errors, error_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                trigger_type,
                now_iso,
                now_iso,
                "partial" if partial_errors else "success",
                int(counts.get("links_provided", 0)),
                int(counts.get("links_processed", 0)),
                int(counts.get("tickets_discovered", 0)),
                int(counts.get("tickets_resolved", 0)),
                int(counts.get("unresolved_links", 0)),
                int(counts.get("errors", 0)),
                "\n".join(partial_errors[:5]) if partial_errors else None,
            ),
        )

        conn.execute("DELETE FROM ticket_dependencies_current")

        existing = _load_existing_tickets(conn)
        results = payload.get("results", []) if isinstance(payload.get("results"), list) else []

        for ticket in results:
            if not isinstance(ticket, dict):
                continue
            ticket_key = str(ticket.get("ticket_key", "")).strip()
            if not ticket_key:
                continue

            _insert_ticket_history(
                conn=conn,
                run_id=run_id,
                now_iso=now_iso,
                ticket_key=ticket_key,
                previous=existing.get(ticket_key),
                current_ticket=ticket,
            )

            conn.execute(
                """
                INSERT INTO tickets_current(
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_key) DO UPDATE SET
                    project_key=excluded.project_key,
                    summary=excluded.summary,
                    issue_type=excluded.issue_type,
                    status=excluded.status,
                    priority=excluded.priority,
                    assignee=excluded.assignee,
                    reporter=excluded.reporter,
                    report_date=excluded.report_date,
                    due_date=excluded.due_date,
                    resolution_date=excluded.resolution_date,
                    updated=excluded.updated,
                    story_points=excluded.story_points,
                    time_original_estimate=excluded.time_original_estimate,
                    time_estimate=excluded.time_estimate,
                    time_spent=excluded.time_spent,
                    source_links_json=excluded.source_links_json,
                    dependencies_json=excluded.dependencies_json,
                    last_seen_run_id=excluded.last_seen_run_id,
                    updated_at=excluded.updated_at
                """,
                (
                    ticket_key,
                    _project_key(ticket_key),
                    ticket.get("summary", ""),
                    ticket.get("issue_type", ""),
                    ticket.get("status", ""),
                    ticket.get("priority", ""),
                    ticket.get("assignee", ""),
                    ticket.get("reporter", ""),
                    ticket.get("report_date", ""),
                    ticket.get("due_date"),
                    ticket.get("resolution_date"),
                    ticket.get("updated", ""),
                    ticket.get("story_points"),
                    ticket.get("time_original_estimate"),
                    ticket.get("time_estimate"),
                    ticket.get("time_spent"),
                    _to_json(ticket.get("source_links", [])),
                    _to_json(ticket.get("dependencies", {})),
                    run_id,
                    now_iso,
                ),
            )

            dependencies = ticket.get("dependencies", {}) if isinstance(ticket.get("dependencies"), dict) else {}
            for dependency_type in ("blockers", "blocking", "other_dependencies"):
                dep_rows = dependencies.get(dependency_type, [])
                if not isinstance(dep_rows, list):
                    continue
                for dep in dep_rows:
                    if not isinstance(dep, dict):
                        continue
                    target_key = str(dep.get("ticket_key", "")).strip()
                    if not target_key:
                        continue
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO ticket_dependencies_current(
                            source_ticket_key, target_ticket_key, dependency_type,
                            relation_name, relation_description, direction, classification,
                            source_project_key, target_project_key, target_status, last_seen_run_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ticket_key,
                            target_key,
                            dependency_type,
                            dep.get("relation_name", ""),
                            dep.get("relation_description", ""),
                            dep.get("direction", ""),
                            dep.get("classification", ""),
                            _project_key(ticket_key),
                            _project_key(target_key),
                            dep.get("status", ""),
                            run_id,
                        ),
                    )

        unresolved = payload.get("unresolved_links", []) if isinstance(payload.get("unresolved_links"), list) else []
        for unresolved_link in unresolved:
            if not isinstance(unresolved_link, dict):
                continue
            board_link = str(unresolved_link.get("board_link", "")).strip()
            if not board_link:
                continue
            conn.execute(
                """
                INSERT INTO unresolved_link_events(run_id, board_link, board_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    board_link,
                    unresolved_link.get("board_id") or _extract_board_id_from_link(board_link),
                    str(unresolved_link.get("reason", "unknown")),
                    now_iso,
                ),
            )

        conn.commit()

    return run_id


def read_sync_overview() -> dict[str, Any]:
    """Return latest run summary and basic counts for status endpoint."""
    init_db()
    with get_connection() as conn:
        latest = conn.execute(
            """
            SELECT run_id, trigger_type, started_at, completed_at, status,
                   links_provided, links_processed, tickets_discovered, tickets_resolved,
                   unresolved_links, errors, error_summary
            FROM sync_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()

        ticket_count = conn.execute("SELECT COUNT(*) AS count FROM tickets_current").fetchone()["count"]

    if not latest:
        return {
            "last_run": None,
            "ticket_count": ticket_count,
        }

    return {
        "last_run": {
            "run_id": latest["run_id"],
            "trigger_type": latest["trigger_type"],
            "started_at": latest["started_at"],
            "completed_at": latest["completed_at"],
            "status": latest["status"],
            "links_provided": latest["links_provided"],
            "links_processed": latest["links_processed"],
            "tickets_discovered": latest["tickets_discovered"],
            "tickets_resolved": latest["tickets_resolved"],
            "unresolved_links": latest["unresolved_links"],
            "errors": latest["errors"],
            "error_summary": latest["error_summary"],
        },
        "ticket_count": ticket_count,
    }


def _append_exact_multi_filter(
    where_parts: list[str],
    params: list[Any],
    column_name: str,
    values: list[str],
) -> None:
    if not values:
        return
    placeholders = ", ".join("?" for _ in values)
    where_parts.append(f"{column_name} IN ({placeholders})")
    params.extend(values)


def _append_exclusion_multi_filter(
    where_parts: list[str],
    params: list[Any],
    column_name: str,
    values: list[str],
) -> None:
    if not values:
        return
    placeholders = ", ".join("?" for _ in values)
    where_parts.append(f"{column_name} NOT IN ({placeholders})")
    params.extend(values)


def _build_ticket_filter_clause(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
    table_alias: str = "",
) -> tuple[str, list[Any]]:
    prefix = f"{table_alias}." if table_alias else ""
    where_parts: list[str] = []
    params: list[Any] = []

    _append_exact_multi_filter(where_parts, params, f"{prefix}status", statuses)
    _append_exact_multi_filter(where_parts, params, f"{prefix}assignee", assignees)
    _append_exclusion_multi_filter(where_parts, params, f"{prefix}status", excluded_statuses)
    _append_exclusion_multi_filter(where_parts, params, f"{prefix}assignee", excluded_assignees)

    if search:
        where_parts.append(f"({prefix}ticket_key LIKE ? OR {prefix}summary LIKE ?)")
        like_value = f"%{search}%"
        params.extend([like_value, like_value])

    if board_id:
        where_parts.append(f"{prefix}source_links_json LIKE ?")
        params.append(f"%/boards/{board_id}%")

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    return where_clause, params


def _extend_where_clause(where_clause: str, extra_condition: str) -> str:
    if where_clause:
        return f"{where_clause} AND {extra_condition}"
    return f"WHERE {extra_condition}"


def _append_team_filter_exists(
    where_parts: list[str],
    params: list[Any],
    assignee_sql: str,
    team_values: list[str],
) -> None:
    if not team_values:
        return

    placeholders = ", ".join("?" for _ in team_values)
    where_parts.append(
        "(" 
        "EXISTS ("
        "SELECT 1 "
        "FROM team_members tm "
        "JOIN teams t ON t.team_id = tm.team_id "
        f"WHERE LOWER(TRIM(tm.display_name)) = LOWER(TRIM({assignee_sql})) "
        f"AND (tm.team_id IN ({placeholders}) OR t.display_name IN ({placeholders}))"
        ")"
        ")"
    )
    params.extend(team_values)
    params.extend(team_values)


def _status_bucket(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in DONE_STATUS_KEYS:
        return "done"
    if normalized in IN_PROGRESS_STATUS_KEYS:
        return "in_progress"
    return "todo"


def _ticket_from_row(row: sqlite3.Row) -> dict[str, Any]:
    source_links = json.loads(row["source_links_json"] or "[]")
    dependencies = json.loads(row["dependencies_json"] or "{}")
    return {
        "ticket_key": row["ticket_key"],
        "project_key": row["project_key"],
        "summary": row["summary"],
        "status": row["status"],
        "assignee": row["assignee"],
        "priority": row["priority"],
        "issue_type": row["issue_type"],
        "reporter": row["reporter"],
        "updated": row["updated"],
        "due_date": row["due_date"],
        "story_points": row["story_points"],
        "time_estimate": row["time_estimate"],
        "time_spent": row["time_spent"],
        "source_links": source_links,
        "dependencies": dependencies,
        "team_id": row["team_id"] if "team_id" in row.keys() else None,
        "team_name": row["team_name"] if "team_name" in row.keys() else None,
    }


def load_filter_options(
    search: str | None,
    board_id: str | None,
    statuses: list[str] | None = None,
    assignees: list[str] | None = None,
    excluded_statuses: list[str] | None = None,
    excluded_assignees: list[str] | None = None,
    teams: list[str] | None = None,
) -> dict[str, list[str]]:
    """Return status/assignee options from filtered ticket scope."""
    statuses = statuses or []
    assignees = assignees or []
    excluded_statuses = excluded_statuses or []
    excluded_assignees = excluded_assignees or []
    teams = teams or []

    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    query_params = list(params)
    _append_team_filter_exists(where_parts, query_params, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        status_rows = conn.execute(
            f"""
            SELECT DISTINCT tc.status
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.status COLLATE NOCASE ASC
            """,
            query_params,
        ).fetchall()

        assignee_rows = conn.execute(
            f"""
            SELECT DISTINCT tc.assignee
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.assignee COLLATE NOCASE ASC
            """,
            query_params,
        ).fetchall()

        team_rows = conn.execute(
            f"""
            SELECT DISTINCT t.team_id, t.display_name
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.team_id
            JOIN tickets_current tc ON LOWER(TRIM(tc.assignee)) = LOWER(TRIM(tm.display_name))
            {scoped_where_clause}
            ORDER BY t.display_name COLLATE NOCASE ASC
            """,
            query_params,
        ).fetchall()

    statuses = [str(row["status"]).strip() for row in status_rows if str(row["status"] or "").strip()]
    assignees = [
        str(row["assignee"]).strip()
        for row in assignee_rows
        if str(row["assignee"] or "").strip()
    ]

    return {
        "statuses": statuses,
        "assignees": assignees,
        "teams": [str(row["display_name"] or "").strip() for row in team_rows if str(row["display_name"] or "").strip()],
    }


def load_ticket_rows(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Return filtered ticket rows and total count."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    params_with_teams = list(params)
    _append_team_filter_exists(where_parts, params_with_teams, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        count_query = f"SELECT COUNT(*) AS count FROM tickets_current tc {scoped_where_clause}"
        total = int(conn.execute(count_query, params_with_teams).fetchone()["count"])

        query = f"""
            SELECT tc.*, mt.team_id, mt.team_name
            FROM tickets_current tc
            LEFT JOIN (
                SELECT LOWER(TRIM(tm.display_name)) AS member_name,
                       MIN(t.team_id) AS team_id,
                       MIN(t.display_name) AS team_name
                FROM team_members tm
                JOIN teams t ON t.team_id = tm.team_id
                GROUP BY LOWER(TRIM(tm.display_name))
            ) mt ON mt.member_name = LOWER(TRIM(tc.assignee))
            {scoped_where_clause}
            ORDER BY tc.updated DESC, tc.ticket_key ASC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, [*params_with_teams, limit, offset]).fetchall()

    items = [_ticket_from_row(row) for row in rows]
    return total, items


def load_ticket_team_groups(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
) -> list[dict[str, Any]]:
    """Return Team -> Member grouped ticket hierarchy with summary badges."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )
    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    params_with_teams = list(params)
    _append_team_filter_exists(where_parts, params_with_teams, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT
                tc.*,
                t.team_id,
                t.display_name AS team_name
            FROM tickets_current tc
            JOIN team_members tm ON LOWER(TRIM(tm.display_name)) = LOWER(TRIM(tc.assignee))
            JOIN teams t ON t.team_id = tm.team_id
            {scoped_where_clause}
            ORDER BY t.display_name COLLATE NOCASE ASC, tc.assignee COLLATE NOCASE ASC, tc.updated DESC
            """,
            params_with_teams,
        ).fetchall()

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        team_id = str(row["team_id"] or "").strip()
        team_name = str(row["team_name"] or "").strip() or "Unmapped Team"
        assignee = str(row["assignee"] or "").strip() or "Unassigned"
        ticket = _ticket_from_row(row)
        team_group = grouped.setdefault(
            team_id,
            {
                "team_id": team_id,
                "team_name": team_name,
                "total_tickets": 0,
                "in_progress_tickets": 0,
                "blocked_tickets": 0,
                "members": {},
            },
        )

        team_group["total_tickets"] += 1
        if _status_bucket(ticket.get("status") or "") == "in_progress":
            team_group["in_progress_tickets"] += 1
        dependencies = ticket.get("dependencies") or {}
        blockers = dependencies.get("blockers") if isinstance(dependencies, dict) else []
        if isinstance(blockers, list) and blockers:
            team_group["blocked_tickets"] += 1

        member_group = team_group["members"].setdefault(
            assignee,
            {
                "assignee": assignee,
                "count": 0,
                "items": [],
            },
        )
        member_group["count"] += 1
        member_group["items"].append(ticket)

    groups: list[dict[str, Any]] = []
    for group in grouped.values():
        members = list(group["members"].values())
        members.sort(key=lambda item: (-int(item["count"]), str(item["assignee"]).casefold()))
        groups.append(
            {
                "team_id": group["team_id"],
                "team_name": group["team_name"],
                "total_tickets": group["total_tickets"],
                "in_progress_tickets": group["in_progress_tickets"],
                "blocked_tickets": group["blocked_tickets"],
                "members": members,
            }
        )

    groups.sort(key=lambda item: (str(item["team_name"]).casefold(), str(item["team_id"])))
    return groups


def load_team_roster(team_filters: list[str] | None = None) -> list[dict[str, Any]]:
    """Return all teams with member roster and external profile URLs."""
    team_filters = team_filters or []
    where_clause = ""
    params: list[Any] = []
    if team_filters:
        placeholders = ", ".join("?" for _ in team_filters)
        where_clause = f"WHERE (t.team_id IN ({placeholders}) OR t.display_name IN ({placeholders}))"
        params.extend(team_filters)
        params.extend(team_filters)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                t.team_id,
                t.display_name AS team_name,
                t.description,
                tm.account_id,
                tm.display_name AS member_name,
                tm.email,
                tm.profile_url
            FROM teams t
            LEFT JOIN team_members tm ON tm.team_id = t.team_id
            {where_clause}
            ORDER BY t.display_name COLLATE NOCASE ASC, tm.display_name COLLATE NOCASE ASC
            """,
            params,
        ).fetchall()

    team_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        team_id = str(row["team_id"] or "").strip()
        if not team_id:
            continue
        team_entry = team_map.setdefault(
            team_id,
            {
                "team_id": team_id,
                "team_name": str(row["team_name"] or "").strip() or "Unnamed Team",
                "description": str(row["description"] or "").strip(),
                "members": [],
            },
        )
        account_id = str(row["account_id"] or "").strip()
        member_name = str(row["member_name"] or "").strip()
        if not account_id and not member_name:
            continue
        team_entry["members"].append(
            {
                "account_id": account_id,
                "display_name": member_name,
                "email": str(row["email"] or "").strip(),
                "profile_url": str(row["profile_url"] or "").strip(),
            }
        )

    teams = list(team_map.values())
    teams.sort(key=lambda item: str(item["team_name"]).casefold())
    return teams


def load_team_workspace_overview(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return team cards with assigned/reported totals for the Teams workspace."""
    roster = load_team_roster(team_filters=teams)
    grouped = load_ticket_team_groups(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=teams,
        search=search,
        board_id=board_id,
    )
    grouped_by_team = {str(item.get("team_id") or ""): item for item in grouped}

    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )
    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    params_with_teams = list(params)
    _append_team_filter_exists(where_parts, params_with_teams, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        reported_rows = conn.execute(
            f"""
            SELECT t.team_id, COUNT(DISTINCT tc.ticket_key) AS reported_count
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.team_id
            LEFT JOIN tickets_current tc ON LOWER(TRIM(tc.reporter)) = LOWER(TRIM(tm.display_name))
            {scoped_where_clause}
            GROUP BY t.team_id
            """,
            params_with_teams,
        ).fetchall()

    reported_by_team = {str(row["team_id"]): int(row["reported_count"] or 0) for row in reported_rows}

    cards: list[dict[str, Any]] = []
    for team in roster:
        team_id = str(team.get("team_id") or "")
        grouped_stats = grouped_by_team.get(team_id, {})
        cards.append(
            {
                "team_id": team_id,
                "team_name": team.get("team_name", ""),
                "description": team.get("description", ""),
                "member_count": len(team.get("members", [])),
                "members": team.get("members", []),
                "metrics": {
                    "total_assigned": int(grouped_stats.get("total_tickets") or 0),
                    "in_progress": int(grouped_stats.get("in_progress_tickets") or 0),
                    "blocked": int(grouped_stats.get("blocked_tickets") or 0),
                    "reported": int(reported_by_team.get(team_id, 0)),
                },
            }
        )

    return {
        "teams": cards,
        "counts": {
            "teams": len(cards),
            "members": sum(int(card.get("member_count") or 0) for card in cards),
        },
    }


def load_team_detail_tabs(
    team_id: str,
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return assigned/work-done/reported/timeline datasets for a selected team."""
    team_filters = [team_id]
    grouped = load_ticket_team_groups(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=team_filters,
        search=search,
        board_id=board_id,
    )
    team_group = grouped[0] if grouped else {
        "team_id": team_id,
        "team_name": "",
        "total_tickets": 0,
        "in_progress_tickets": 0,
        "blocked_tickets": 0,
        "members": [],
    }

    assigned_items: list[dict[str, Any]] = []
    for member in team_group.get("members", []):
        assigned_items.extend(member.get("items", []))

    work_done = [item for item in assigned_items if _status_bucket(str(item.get("status") or "")) == "done"]

    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )
    where_parts: list[str] = ["t.team_id = ?"]
    params_with_team = [team_id]
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    params_with_team.extend(params)
    reported_where = f"WHERE {' AND '.join(where_parts)}"

    with get_connection() as conn:
        reported_rows = conn.execute(
            f"""
            SELECT DISTINCT tc.*
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.team_id
            JOIN tickets_current tc ON LOWER(TRIM(tc.reporter)) = LOWER(TRIM(tm.display_name))
            {reported_where}
            ORDER BY tc.updated DESC, tc.ticket_key ASC
            """,
            params_with_team,
        ).fetchall()

    reported_items = [_ticket_from_row(row) for row in reported_rows]

    timeline = {
        "todo": 0,
        "in_progress": 0,
        "done": 0,
        "total": len(assigned_items),
    }
    for item in assigned_items:
        bucket = _status_bucket(str(item.get("status") or ""))
        timeline[bucket] += 1

    return {
        "team": {
            "team_id": team_group.get("team_id"),
            "team_name": team_group.get("team_name"),
        },
        "tickets_assigned": {
            "metrics": {
                "total": int(team_group.get("total_tickets") or 0),
                "in_progress": int(team_group.get("in_progress_tickets") or 0),
                "blocked": int(team_group.get("blocked_tickets") or 0),
            },
            "items": assigned_items,
        },
        "work_done": {
            "count": len(work_done),
            "items": work_done,
        },
        "tickets_reported": {
            "count": len(reported_items),
            "items": reported_items,
        },
        "timeline": timeline,
    }


def load_team_filter_options(
    search: str | None,
    board_id: str | None,
    selected_teams: list[str],
) -> dict[str, list[str]]:
    """Return filter options with team list and cascaded assignee options."""
    return load_filter_options(
        search=search,
        board_id=board_id,
        teams=selected_teams,
    )


def load_grouped_tickets_by_team(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return Team -> Member grouped payload compatible with tickets endpoint."""
    total, rows = load_ticket_rows(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=teams,
        search=search,
        board_id=board_id,
        limit=limit,
        offset=offset,
    )

    groups = load_ticket_team_groups(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=teams,
        search=search,
        board_id=board_id,
    )

    # Preserve paging total while exposing grouped payload.
    return {
        "total": total,
        "items": rows,
        "groups": [
            {
                "team_id": group.get("team_id"),
                "team_name": group.get("team_name"),
                "metrics": {
                    "total": group.get("total_tickets", 0),
                    "in_progress": group.get("in_progress_tickets", 0),
                    "blocked": group.get("blocked_tickets", 0),
                },
                "members": [
                    {
                        "member_name": member.get("assignee", ""),
                        "count": member.get("count", 0),
                        "items": member.get("items", []),
                    }
                    for member in group.get("members", [])
                ],
            }
            for group in groups
        ],
    }


def load_teams_workspace_data() -> dict[str, Any]:
    """Return data payload for teams workspace."""
    return load_team_workspace_overview(
        statuses=[],
        assignees=[],
        excluded_statuses=[],
        excluded_assignees=[],
        teams=[],
        search=None,
        board_id=None,
    )


def load_team_detail_panels(
    team_id: str,
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return team detail panel payload for the frontend tabs."""
    return load_team_detail_tabs(
        team_id=team_id,
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
    )


def calculate_metrics(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return dashboard KPI and dependency metrics for filtered ticket scope."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    scoped_params = list(params)
    _append_team_filter_exists(where_parts, scoped_params, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        by_status_rows = conn.execute(
            f"""
            SELECT tc.status, COUNT(*) AS count
            FROM tickets_current tc
            {scoped_where_clause}
            GROUP BY tc.status
            ORDER BY tc.status ASC
            """,
            scoped_params,
        ).fetchall()

        active_tickets = sum(int(row["count"]) for row in by_status_rows)

        open_bug_count = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM tickets_current tc
                {_extend_where_clause(scoped_where_clause, "LOWER(tc.issue_type) = 'bug' AND (tc.resolution_date IS NULL OR tc.resolution_date = '')")}
                """,
                scoped_params,
            ).fetchone()["count"]
        )

        stale_tickets = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM tickets_current tc
                {_extend_where_clause(scoped_where_clause, "(tc.updated IS NULL OR tc.updated = '' OR datetime(tc.updated) <= datetime('now', '-14 day'))")}
                """,
                scoped_params,
            ).fetchone()["count"]
        )

        dependency_where_clause = scoped_where_clause.replace("WHERE", "", 1).strip()
        if dependency_where_clause:
            dependency_where = (
                "WHERE source_ticket_key IN (SELECT tc.ticket_key FROM tickets_current tc "
                f"{scoped_where_clause})"
            )
            dependency_params = scoped_params
        else:
            dependency_where = ""
            dependency_params = []

        blockers = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ticket_dependencies_current
                {dependency_where}
                {'AND' if dependency_where else 'WHERE'} dependency_type = 'blockers'
                """,
                dependency_params,
            ).fetchone()["count"]
        )

        inter_team = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ticket_dependencies_current
                {dependency_where}
                {'AND' if dependency_where else 'WHERE'} classification = 'inter_team'
                """,
                dependency_params,
            ).fetchone()["count"]
        )

        intra_team = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ticket_dependencies_current
                {dependency_where}
                {'AND' if dependency_where else 'WHERE'} classification = 'intra_team'
                """,
                dependency_params,
            ).fetchone()["count"]
        )

    return {
        "kpis": {
            "total_active_tickets": active_tickets,
            "open_bug_count": open_bug_count,
            "stale_tickets_over_14_days": stale_tickets,
        },
        "active_by_status": [
            {"status": row["status"] or "Unknown", "count": int(row["count"])} for row in by_status_rows
        ],
        "dependency_summary": {
            "blockers": blockers,
            "inter_team": inter_team,
            "intra_team": intra_team,
        },
    }


def build_network_graph(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return network graph nodes/edges from filtered ticket scope and dependencies."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    scoped_params = list(params)
    _append_team_filter_exists(where_parts, scoped_params, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        ticket_rows = conn.execute(
            f"""
            SELECT tc.ticket_key, tc.summary, tc.status, tc.assignee, tc.priority, tc.reporter, tc.issue_type, tc.story_points
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.ticket_key ASC
            """,
            scoped_params,
        ).fetchall()

        edge_where_clause = (
            "WHERE source_ticket_key IN (SELECT tc.ticket_key FROM tickets_current tc "
            f"{scoped_where_clause})"
            if scoped_where_clause
            else ""
        )
        edge_params = [*scoped_params] if scoped_where_clause else []

        dep_rows = conn.execute(
            f"""
            SELECT source_ticket_key, target_ticket_key, relation_name, relation_description,
                   dependency_type, classification, target_status
            FROM ticket_dependencies_current
            {edge_where_clause}
            ORDER BY source_ticket_key ASC, target_ticket_key ASC
            """,
            edge_params,
        ).fetchall()

        node_map: dict[str, dict[str, Any]] = {
            str(row["ticket_key"]): {
                "id": row["ticket_key"],
                "ticket_key": row["ticket_key"],
                "summary": row["summary"],
                "status": row["status"],
                "assignee": row["assignee"],
                "priority": row["priority"],
                "reporter": row["reporter"],
                "issue_type": row["issue_type"],
                "story_points": row["story_points"],
            }
            for row in ticket_rows
        }

        target_status_by_key: dict[str, str] = {}
        missing_target_keys: set[str] = set()
        for row in dep_rows:
            target_key = str(row["target_ticket_key"] or "").strip()
            if not target_key:
                continue
            if target_key not in node_map:
                missing_target_keys.add(target_key)
            target_status_by_key[target_key] = str(row["target_status"] or "").strip()

        if missing_target_keys:
            placeholders = ", ".join("?" for _ in missing_target_keys)
            external_rows = conn.execute(
                f"""
                SELECT ticket_key, summary, status, assignee, priority, reporter, issue_type, story_points
                FROM tickets_current
                WHERE ticket_key IN ({placeholders})
                """,
                list(missing_target_keys),
            ).fetchall()

            for row in external_rows:
                node_map[str(row["ticket_key"])] = {
                    "id": row["ticket_key"],
                    "ticket_key": row["ticket_key"],
                    "summary": row["summary"],
                    "status": row["status"],
                    "assignee": row["assignee"],
                    "priority": row["priority"],
                    "reporter": row["reporter"],
                    "issue_type": row["issue_type"],
                    "story_points": row["story_points"],
                }

        for target_key in missing_target_keys:
            if target_key in node_map:
                continue
            node_map[target_key] = {
                "id": target_key,
                "ticket_key": target_key,
                "summary": "Dependency target outside cached ticket scope",
                "status": target_status_by_key.get(target_key, "Unknown"),
                "assignee": "",
                "priority": "",
                "reporter": "",
                "issue_type": "",
                "story_points": None,
            }

    connected_keys: set[str] = set()
    edges: list[dict[str, Any]] = []
    for row in dep_rows:
        source_key = str(row["source_ticket_key"] or "").strip()
        target_key = str(row["target_ticket_key"] or "").strip()
        if not source_key or not target_key:
            continue
        connected_keys.add(source_key)
        connected_keys.add(target_key)
        edges.append(
            {
                "source_ticket": source_key,
                "target_ticket": target_key,
                "relation_name": row["relation_name"],
                "relation_description": row["relation_description"],
                "dependency_type": row["dependency_type"],
                "classification": row["classification"],
            }
        )

    nodes = sorted(
        [node for key, node in node_map.items() if key in connected_keys],
        key=lambda node: str(node.get("ticket_key") or ""),
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
        },
    }
