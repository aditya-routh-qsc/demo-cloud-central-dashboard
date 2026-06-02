"""FastAPI backend for cached Jira dashboard data."""

from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config_utils import get_sync_interval_minutes
from database import get_connection, init_db, persist_extraction_result, read_sync_overview
from services import _get_runtime_inputs, get_ticket_details_from_kanban_links

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:  # pragma: no cover - fallback path when APScheduler is unavailable
    BackgroundScheduler = None  # type: ignore[assignment]


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and shutdown background scheduler with app lifecycle."""
    global _scheduler

    init_db()

    if BackgroundScheduler is not None:
        interval_minutes = get_sync_interval_minutes()
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(
            _scheduled_sync_job,
            "interval",
            minutes=interval_minutes,
            id="periodic_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        _scheduler.start()

    try:
        yield
    finally:
        if _scheduler is not None:
            _scheduler.shutdown(wait=False)
            _scheduler = None

app = FastAPI(title="Cloud Central Dashboard API", version="1.0.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scheduler: Any = None
_sync_lock = threading.Lock()
_state_lock = threading.Lock()
_manual_requested = False
_sync_running = False
_current_sync_trigger = ""
_current_sync_started_at = ""
_last_sync_error = ""
_frontend_dir = Path(__file__).parent / "frontend"


if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir)), name="frontend-assets")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_sync(message: str) -> None:
    # Keep sync lifecycle visible in server logs for long-running manual operations.
    print(f"[{_utc_now()}] [sync] {message}", flush=True)


def _parse_multi_query_values(raw_values: list[str] | None, allow_csv: bool = False) -> list[str]:
    parsed: list[str] = []
    seen: set[str] = set()
    for raw in raw_values or []:
        pieces = str(raw).split(",") if allow_csv else [str(raw)]
        for piece in pieces:
            value = piece.strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            parsed.append(value)
    return parsed


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
) -> tuple[str, list[Any]]:
    where_parts: list[str] = []
    params: list[Any] = []

    _append_exact_multi_filter(where_parts, params, "status", statuses)
    _append_exact_multi_filter(where_parts, params, "assignee", assignees)
    _append_exclusion_multi_filter(where_parts, params, "status", excluded_statuses)
    _append_exclusion_multi_filter(where_parts, params, "assignee", excluded_assignees)

    if search:
        where_parts.append("(ticket_key LIKE ? OR summary LIKE ?)")
        like_value = f"%{search}%"
        params.extend([like_value, like_value])

    if board_id:
        where_parts.append("source_links_json LIKE ?")
        params.append(f"%/boards/{board_id}%")

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    return where_clause, params


def _extend_where_clause(where_clause: str, extra_condition: str) -> str:
    if where_clause:
        return f"{where_clause} AND {extra_condition}"
    return f"WHERE {extra_condition}"


def _load_filter_options(search: str | None, board_id: str | None) -> dict[str, list[str]]:
    where_clause, params = _build_ticket_filter_clause(
        statuses=[],
        assignees=[],
        excluded_statuses=[],
        excluded_assignees=[],
        search=search,
        board_id=board_id,
    )

    with get_connection() as conn:
        status_rows = conn.execute(
            f"""
            SELECT DISTINCT status
            FROM tickets_current
            {where_clause}
            ORDER BY status COLLATE NOCASE ASC
            """,
            params,
        ).fetchall()

        assignee_rows = conn.execute(
            f"""
            SELECT DISTINCT assignee
            FROM tickets_current
            {where_clause}
            ORDER BY assignee COLLATE NOCASE ASC
            """,
            params,
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
    }


def _group_tickets_by_assignee(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        assignee = str(item.get("assignee") or "").strip() or "Unassigned"
        grouped.setdefault(assignee, []).append(item)

    groups = [
        {
            "assignee": assignee,
            "count": len(rows),
            "items": rows,
        }
        for assignee, rows in grouped.items()
    ]
    groups.sort(key=lambda group: (-int(group["count"]), str(group["assignee"]).casefold()))
    return groups


def _load_ticket_rows(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
    )

    with get_connection() as conn:
        count_query = f"SELECT COUNT(*) AS count FROM tickets_current {where_clause}"
        total = int(conn.execute(count_query, params).fetchone()["count"])

        query = f"""
            SELECT *
            FROM tickets_current
            {where_clause}
            ORDER BY updated DESC, ticket_key ASC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, [*params, limit, offset]).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        source_links = json.loads(row["source_links_json"] or "[]")
        dependencies = json.loads(row["dependencies_json"] or "{}")
        items.append(
            {
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
            }
        )
    return total, items


def _calculate_metrics(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
    )

    with get_connection() as conn:
        by_status_rows = conn.execute(
            f"""
            SELECT status, COUNT(*) AS count
            FROM tickets_current
            {where_clause}
            GROUP BY status
            ORDER BY status ASC
            """,
            params,
        ).fetchall()

        active_tickets = sum(int(row["count"]) for row in by_status_rows)

        open_bug_count = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM tickets_current
                {_extend_where_clause(where_clause, "LOWER(issue_type) = 'bug' AND (resolution_date IS NULL OR resolution_date = '')")}
                """,
                params,
            ).fetchone()["count"]
        )

        stale_tickets = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM tickets_current
                {_extend_where_clause(where_clause, "(updated IS NULL OR updated = '' OR datetime(updated) <= datetime('now', '-14 day'))")}
                """,
                params,
            ).fetchone()["count"]
        )

        dependency_where_clause = where_clause.replace("WHERE", "", 1).strip()
        if dependency_where_clause:
            dependency_where = (
                "WHERE source_ticket_key IN (SELECT ticket_key FROM tickets_current "
                f"{where_clause})"
            )
            dependency_params = params
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


def _build_network_graph(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
    )

    with get_connection() as conn:
        ticket_rows = conn.execute(
            f"""
            SELECT ticket_key, summary, status, assignee, priority, reporter, issue_type, story_points
            FROM tickets_current
            {where_clause}
            ORDER BY ticket_key ASC
            """,
            params,
        ).fetchall()

        edge_where_clause = (
            "WHERE source_ticket_key IN (SELECT ticket_key FROM tickets_current "
            f"{where_clause})"
            if where_clause
            else ""
        )
        edge_params = [*params] if where_clause else []

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

    nodes = sorted(node_map.values(), key=lambda node: str(node.get("ticket_key") or ""))

    edges = [
        {
            "source_ticket": row["source_ticket_key"],
            "target_ticket": row["target_ticket_key"],
            "relation_name": row["relation_name"],
            "relation_description": row["relation_description"],
            "dependency_type": row["dependency_type"],
            "classification": row["classification"],
        }
        for row in dep_rows
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
        },
    }


def _run_single_sync(trigger_type: str) -> str:
    global _sync_running, _current_sync_trigger, _current_sync_started_at, _last_sync_error

    _log_sync(f"starting {trigger_type} sync")

    with _state_lock:
        _sync_running = True
        _current_sync_trigger = trigger_type
        _current_sync_started_at = _utc_now()
        _last_sync_error = ""

    try:
        runtime_inputs = _get_runtime_inputs()
        _log_sync(f"resolved runtime inputs: kanban_links={len(runtime_inputs.get('kanban_links', []))}")
        response = get_ticket_details_from_kanban_links(runtime_inputs["kanban_links"])
        counts = response.get("counts", {}) if isinstance(response, dict) else {}
        _log_sync(
            "extraction completed: "
            f"links_processed={counts.get('links_processed', 0)}, "
            f"tickets_resolved={counts.get('tickets_resolved', 0)}, "
            f"errors={counts.get('errors', 0)}"
        )
        run_id = persist_extraction_result(response, trigger_type=trigger_type)
        _log_sync(f"persisted sync run_id={run_id}")
        return run_id
    except Exception as exc:  # noqa: BLE001
        with _state_lock:
            _last_sync_error = str(exc)
        _log_sync(f"sync failed: {exc}")
        raise
    finally:
        with _state_lock:
            _sync_running = False
            _current_sync_trigger = ""
            _current_sync_started_at = ""
        _log_sync(f"finished {trigger_type} sync")


def _sync_worker(initial_trigger: str) -> None:
    global _manual_requested
    trigger = initial_trigger

    while True:
        with _sync_lock:
            try:
                _run_single_sync(trigger)
            except Exception:  # noqa: BLE001
                break

        with _state_lock:
            should_run_manual_next = trigger == "scheduled" and _manual_requested
            if should_run_manual_next:
                _manual_requested = False

        if not should_run_manual_next:
            break
        trigger = "manual"


def _start_sync_thread(trigger_type: str) -> dict[str, Any]:
    global _manual_requested, _sync_running, _current_sync_trigger, _current_sync_started_at, _last_sync_error

    with _state_lock:
        if _sync_running:
            if trigger_type == "manual":
                _manual_requested = True
                _log_sync("manual sync requested while running; queued next")
                return {
                    "accepted": True,
                    "queued": True,
                    "message": "Manual sync queued and prioritized after current run.",
                }
            _log_sync("scheduled sync skipped because another sync is running")
            return {
                "accepted": False,
                "queued": False,
                "message": "Scheduled sync skipped because another sync is running.",
            }

        # Reserve sync slot before starting thread to avoid launch race between requests.
        _sync_running = True
        _current_sync_trigger = trigger_type
        _current_sync_started_at = _utc_now()
        _last_sync_error = ""

    thread = threading.Thread(target=_sync_worker, args=(trigger_type,), daemon=True)
    thread.start()
    _log_sync(f"sync worker thread started for trigger={trigger_type}")
    return {
        "accepted": True,
        "queued": False,
        "message": f"{trigger_type.capitalize()} sync started.",
    }


def _scheduled_sync_job() -> None:
    _start_sync_thread("scheduled")


@app.get("/")
def get_dashboard_app() -> FileResponse:
    index_path = _frontend_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(path=str(index_path))


@app.get("/api/sync/status")
def get_sync_status() -> dict[str, Any]:
    with _state_lock:
        runtime_state = {
            "is_running": _sync_running,
            "trigger": _current_sync_trigger,
            "started_at": _current_sync_started_at,
            "manual_requested": _manual_requested,
            "last_error": _last_sync_error,
        }

    persisted = read_sync_overview()
    return {
        "runtime": runtime_state,
        "persisted": persisted,
    }


@app.post("/api/sync/manual")
def start_manual_sync() -> dict[str, Any]:
    return _start_sync_thread("manual")


@app.get("/api/tickets")
def get_tickets(
    status: list[str] | None = Query(default=None),
    assignee: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    # Keep CSV fallback for status for URL backward-compat; assignee names may contain commas.
    status_values = _parse_multi_query_values(status, allow_csv=True)
    assignee_values = _parse_multi_query_values(assignee, allow_csv=False)
    excluded_status_values = _parse_multi_query_values(status_exclude, allow_csv=True)
    excluded_assignee_values = _parse_multi_query_values(assignee_exclude, allow_csv=False)

    total, rows = _load_ticket_rows(
        statuses=status_values,
        assignees=assignee_values,
        excluded_statuses=excluded_status_values,
        excluded_assignees=excluded_assignee_values,
        search=search,
        board_id=board_id,
        limit=limit,
        offset=offset,
    )

    filter_options = _load_filter_options(search=search, board_id=board_id)
    grouped = _group_tickets_by_assignee(rows)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": rows,
        "filter_options": filter_options,
        "groups": grouped,
    }


@app.get("/api/metrics")
def get_metrics(
    status: list[str] | None = Query(default=None),
    assignee: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return _calculate_metrics(
        statuses=_parse_multi_query_values(status, allow_csv=True),
        assignees=_parse_multi_query_values(assignee, allow_csv=False),
        excluded_statuses=_parse_multi_query_values(status_exclude, allow_csv=True),
        excluded_assignees=_parse_multi_query_values(assignee_exclude, allow_csv=False),
        search=search,
        board_id=board_id,
    )


@app.get("/api/network")
def get_network(
    status: list[str] | None = Query(default=None),
    assignee: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return _build_network_graph(
        statuses=_parse_multi_query_values(status, allow_csv=True),
        assignees=_parse_multi_query_values(assignee, allow_csv=False),
        excluded_statuses=_parse_multi_query_values(status_exclude, allow_csv=True),
        excluded_assignees=_parse_multi_query_values(assignee_exclude, allow_csv=False),
        search=search,
        board_id=board_id,
    )
