"""Smoke checks for dashboard frontend/API contract alignment."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import get_metrics, get_network, get_sync_status, get_tickets


def assert_keys(payload: dict, required: list[str], label: str) -> None:
    missing = [key for key in required if key not in payload]
    if missing:
        raise AssertionError(f"{label} missing keys: {missing}")


def run_smoke_checks() -> None:
    frontend_root = Path(__file__).resolve().parent.parent / "frontend"
    if not (frontend_root / "index.html").exists():
        raise AssertionError("frontend/index.html missing")
    if not (frontend_root / "app.js").exists():
        raise AssertionError("frontend/app.js missing")
    if not (frontend_root / "style.css").exists():
        raise AssertionError("frontend/style.css missing")

    index_html = (frontend_root / "index.html").read_text(encoding="utf-8")
    app_js = (frontend_root / "app.js").read_text(encoding="utf-8")
    style_css = (frontend_root / "style.css").read_text(encoding="utf-8")

    if "limitInput" in index_html or "Rows" in index_html:
        raise AssertionError("Rows filter control should not be present in frontend/index.html")
    if "limitInput" in app_js or "state.filters.limit" in app_js:
        raise AssertionError("Rows filter state should not be present in frontend/app.js")
    if "toggleAdvancedFiltersBtn" not in index_html or "advancedFilters" not in index_html:
        raise AssertionError("Collapsible advanced filters UI missing from frontend/index.html")
    if "bindFilterDisclosure" not in app_js or "advancedFiltersOpen" not in app_js:
        raise AssertionError("Collapsible advanced filters logic missing from frontend/app.js")
    if "shell-layout" not in index_html or "sidebar" not in index_html:
        raise AssertionError("Side navigation shell missing from frontend/index.html")
    if "shell-layout" not in style_css or "filters-advanced" not in style_css:
        raise AssertionError("Shell layout styles missing from frontend/style.css")
    if "networkLegend" not in index_html:
        raise AssertionError("Network legend container missing from frontend/index.html")
    if "legend-grid" not in style_css or "legend-swatch" not in style_css:
        raise AssertionError("Network legend styles missing from frontend/style.css")
    if "issue_type_key" not in app_js or "dependency_type_key" not in app_js:
        raise AssertionError("Graph semantic keys missing from frontend/app.js")

    sync_payload = get_sync_status()
    assert_keys(sync_payload, ["runtime", "persisted"], "sync status")

    metrics_payload = get_metrics(
        status=["To Do"],
        assignee=None,
        status_exclude=[],
        assignee_exclude=[],
        search=None,
        board_id=None,
    )
    assert_keys(metrics_payload, ["kpis", "active_by_status", "dependency_summary"], "metrics")

    tickets_payload = get_tickets(
        status=["To Do", "In Progress"],
        assignee=None,
        status_exclude=[],
        assignee_exclude=[],
        search=None,
        board_id=None,
        limit=1000,
        offset=0,
    )
    assert_keys(tickets_payload, ["total", "limit", "offset", "items", "filter_options", "groups"], "tickets")
    if tickets_payload["limit"] != 1000:
        raise AssertionError(f"Expected limit=1000, got {tickets_payload['limit']}")
    assert_keys(tickets_payload["filter_options"], ["statuses", "assignees"], "ticket filter options")
    if not isinstance(tickets_payload["groups"], list):
        raise AssertionError("Expected grouped tickets list")

    network_payload = get_network(
        status=["To Do"],
        assignee=None,
        status_exclude=[],
        assignee_exclude=[],
        search=None,
        board_id=None,
    )
    assert_keys(network_payload, ["nodes", "edges", "counts"], "network")

    print("smoke_ok")


if __name__ == "__main__":
    run_smoke_checks()
