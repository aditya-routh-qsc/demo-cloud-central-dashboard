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

    sync_payload = get_sync_status()
    assert_keys(sync_payload, ["runtime", "persisted"], "sync status")

    metrics_payload = get_metrics(status=["To Do"], assignee=None, search=None, board_id=None)
    assert_keys(metrics_payload, ["kpis", "active_by_status", "dependency_summary"], "metrics")

    tickets_payload = get_tickets(status=["To Do", "In Progress"], assignee=None, search=None, board_id=None, limit=5, offset=0)
    assert_keys(tickets_payload, ["total", "limit", "offset", "items", "filter_options", "groups"], "tickets")
    if tickets_payload["limit"] != 5:
        raise AssertionError(f"Expected limit=5, got {tickets_payload['limit']}")
    assert_keys(tickets_payload["filter_options"], ["statuses", "assignees"], "ticket filter options")
    if not isinstance(tickets_payload["groups"], list):
        raise AssertionError("Expected grouped tickets list")

    network_payload = get_network(status=["To Do"], assignee=None, search=None, board_id=None)
    assert_keys(network_payload, ["nodes", "edges", "counts"], "network")

    print("smoke_ok")


if __name__ == "__main__":
    run_smoke_checks()
