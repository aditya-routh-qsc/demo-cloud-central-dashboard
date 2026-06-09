"""FastAPI backend for cached Jira dashboard data."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config_utils import get_sync_interval_minutes, get_sync_cooldown_seconds
from database import (
    calculate_metrics,
    init_db,
    load_filter_options,
    load_grouped_tickets_by_team,
    load_team_detail_panels,
    load_team_filter_options,
    load_teams_workspace_data,
    load_ticket_rows,
    persist_extraction_result,
    read_sync_overview,
)
from services import _get_runtime_inputs, get_ticket_details_from_kanban_links
import json

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
        _log_sync(f"scheduler configured: interval_minutes={interval_minutes}")
        
        # Guard against reload-loop: only run startup sync if last sync completed > cooldown ago
        run_startup_sync = True
        try:
            persisted = read_sync_overview()
            last_run = persisted.get("last_run")
            if last_run and last_run.get("completed_at"):
                last_completed = datetime.fromisoformat(last_run["completed_at"])
                elapsed = (datetime.now(timezone.utc) - last_completed).total_seconds()
                cooldown = get_sync_cooldown_seconds()
                if elapsed < cooldown:
                    run_startup_sync = False
                    _log_sync(f"skipping startup sync: last sync completed {elapsed:.1f}s ago (< {cooldown}s)")
        except Exception as e:
            _log_sync(f"error checking last sync time: {e}")

        next_run = datetime.now(timezone.utc) if run_startup_sync else None

        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(
            _scheduled_sync_job,
            "interval",
            minutes=interval_minutes,
            id="periodic_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
            next_run_time=next_run,
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
_assets_dir = Path(__file__).parent / "assets"


if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir)), name="frontend-assets")

if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_sync(message: str) -> None:
    # Keep sync lifecycle visible in server logs for long-running manual operations.
    print(f"[{_utc_now()}] [sync] {message}", flush=True)


def _unwrap_query(val: Any, default: Any = None) -> Any:
    if type(val).__name__ == "Query":
        return default
    return val


def _parse_multi_query_values(raw_values: list[str] | None, allow_csv: bool = False) -> list[str]:
    raw_values = _unwrap_query(raw_values, None)
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
    return load_filter_options(search=search, board_id=board_id)


def _load_team_filter_options(
    search: str | None,
    board_id: str | None,
    selected_teams: list[str],
) -> dict[str, list[str]]:
    return load_team_filter_options(search=search, board_id=board_id, selected_teams=selected_teams)


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
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
    limit: int | None,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    return load_ticket_rows(
        statuses=statuses,
        assignees=assignees,
        teams=teams,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        limit=limit,
        offset=offset,
    )


def _calculate_metrics(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    return calculate_metrics(
        statuses=statuses,
        assignees=assignees,
        teams=teams,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
    )


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

        # Run infocomm schedule scraper as part of sync
        _log_sync("starting infocomm schedules scrape as part of sync")
        import asyncio
        from scraper import scrape_schedule, SHOW_URLS, save_to_json
        
        loop = asyncio.new_event_loop()
        try:
            for show, url in SHOW_URLS.items():
                _log_sync(f"scraping infocomm schedule for show: {show} ({url})")
                file_path = Path(__file__).parent / "outputs" / f"infocomm_{show}.json"
                data = loop.run_until_complete(scrape_schedule(url, fallback_path=file_path))
                if data:
                    save_to_json(data, file_path)
                    _log_sync(f"successfully saved infocomm_{show}.json")
                else:
                    _log_sync(f"no data returned for show: {show}")
        except Exception as e:
            _log_sync(f"failed to scrape infocomm schedules: {e}")
        finally:
            loop.close()

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
    team: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    # Keep CSV fallback for status for URL backward-compat; assignee names may contain commas.
    search = _unwrap_query(search, None)
    board_id = _unwrap_query(board_id, None)
    limit = _unwrap_query(limit, None)
    offset = _unwrap_query(offset, 0)
    status_values = _parse_multi_query_values(status, allow_csv=True)
    assignee_values = _parse_multi_query_values(assignee, allow_csv=False)
    team_values = _parse_multi_query_values(team, allow_csv=False)
    excluded_status_values = _parse_multi_query_values(status_exclude, allow_csv=True)
    excluded_assignee_values = _parse_multi_query_values(assignee_exclude, allow_csv=False)

    total, rows = _load_ticket_rows(
        statuses=status_values,
        assignees=assignee_values,
        teams=team_values,
        excluded_statuses=excluded_status_values,
        excluded_assignees=excluded_assignee_values,
        search=search,
        board_id=board_id,
        limit=limit,
        offset=offset,
    )

    filter_options = _load_team_filter_options(
        search=search,
        board_id=board_id,
        selected_teams=team_values,
    )
    grouped_payload = load_grouped_tickets_by_team(
        statuses=status_values,
        assignees=assignee_values,
        teams=team_values,
        excluded_statuses=excluded_status_values,
        excluded_assignees=excluded_assignee_values,
        search=search,
        board_id=board_id,
        limit=limit,
        offset=offset,
    )
    grouped = grouped_payload.get("groups", []) if isinstance(grouped_payload, dict) else _group_tickets_by_assignee(rows)

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
    team: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
) -> dict[str, Any]:
    search = _unwrap_query(search, None)
    board_id = _unwrap_query(board_id, None)
    return _calculate_metrics(
        statuses=_parse_multi_query_values(status, allow_csv=True),
        assignees=_parse_multi_query_values(assignee, allow_csv=False),
        teams=_parse_multi_query_values(team, allow_csv=False),
        excluded_statuses=_parse_multi_query_values(status_exclude, allow_csv=True),
        excluded_assignees=_parse_multi_query_values(assignee_exclude, allow_csv=False),
        search=search,
        board_id=board_id,
    )


@app.get("/api/teams")
def get_teams_workspace(
    status: list[str] | None = Query(default=None),
    assignee: list[str] | None = Query(default=None),
    team: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
) -> dict[str, Any]:
    search = _unwrap_query(search, None)
    board_id = _unwrap_query(board_id, None)
    return load_teams_workspace_data(
        statuses=_parse_multi_query_values(status, allow_csv=True),
        assignees=_parse_multi_query_values(assignee, allow_csv=False),
        teams=_parse_multi_query_values(team, allow_csv=False),
        excluded_statuses=_parse_multi_query_values(status_exclude, allow_csv=True),
        excluded_assignees=_parse_multi_query_values(assignee_exclude, allow_csv=False),
        search=search,
        board_id=board_id,
    )


@app.get("/api/teams/{team_id:path}")
def get_team_details(
    team_id: str,
    status: list[str] | None = Query(default=None),
    assignee: list[str] | None = Query(default=None),
    status_exclude: list[str] | None = Query(default=None),
    assignee_exclude: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
    board_id: str | None = Query(default=None),
) -> dict[str, Any]:
    search = _unwrap_query(search, None)
    board_id = _unwrap_query(board_id, None)
    return load_team_detail_panels(
        team_id=team_id,
        statuses=_parse_multi_query_values(status, allow_csv=True),
        assignees=_parse_multi_query_values(assignee, allow_csv=False),
        excluded_statuses=_parse_multi_query_values(status_exclude, allow_csv=True),
        excluded_assignees=_parse_multi_query_values(assignee_exclude, allow_csv=False),
        search=search,
        board_id=board_id,
    )


@app.get("/api/infocomm/schedule/{show}")
def get_infocomm_schedule(show: str, refresh: bool = False) -> list[dict]:
    if show not in ["india", "asia", "global"]:
        raise HTTPException(status_code=400, detail="Invalid show type")
    
    file_path = _frontend_dir.parent / "outputs" / f"infocomm_{show}.json"
    
    if refresh or not file_path.exists():
        import asyncio
        from scraper import scrape_schedule, SHOW_URLS, save_to_json
        
        url = SHOW_URLS[show]
        try:
            loop = asyncio.new_event_loop()
            data = loop.run_until_complete(scrape_schedule(url, fallback_path=file_path))
            loop.close()
            if data:
                # Persist normalized dates-only payload.
                normalized_dates = []
                seen_dates: set[str] = set()
                for item in data:
                    date_value = str((item or {}).get("date") or "").strip() if isinstance(item, dict) else ""
                    if not date_value or date_value in seen_dates:
                        continue
                    seen_dates.add(date_value)
                    normalized_dates.append({"date": date_value})

                save_to_json(normalized_dates, file_path)
            else:
                raise Exception("Scraper returned empty data")
        except Exception as e:
            if file_path.exists():
                print(f"[!] Scraper failed, falling back to cache: {e}")
            else:
                raise HTTPException(status_code=500, detail=f"Scraping failed: {e}")
                
    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Always return dates-only response shape even if legacy cache exists.
    dates_only: list[dict[str, str]] = []
    seen_dates: set[str] = set()
    for item in payload if isinstance(payload, list) else []:
        if isinstance(item, dict):
            date_value = str(item.get("date") or "").strip()
        else:
            date_value = str(item or "").strip()
        if not date_value or date_value in seen_dates:
            continue
        seen_dates.add(date_value)
        dates_only.append({"date": date_value})

    return dates_only
