"""SQLite connector and persistence helpers for dashboard cache."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
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


@contextmanager
def get_connection() -> sqlite3.Connection:
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

            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets_current(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_assignee ON tickets_current(assignee);
            CREATE INDEX IF NOT EXISTS idx_tickets_updated ON tickets_current(updated);
            CREATE INDEX IF NOT EXISTS idx_deps_source ON ticket_dependencies_current(source_ticket_key);
            CREATE INDEX IF NOT EXISTS idx_deps_target ON ticket_dependencies_current(target_ticket_key);
            CREATE INDEX IF NOT EXISTS idx_history_ticket ON ticket_history_log(ticket_key, changed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_runs_started ON sync_runs(started_at DESC);
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
