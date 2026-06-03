# Cloud Central Dashboard API Contract Sheet

This contract tracks the APIs currently implemented in `main.py`.

## Base Information

- Base URL (local default): `http://127.0.0.1:8000`
- Content type: `application/json`
- Authentication: none (internal/local usage)
- CORS: open (`*`)

## Endpoint Summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/sync/status` | Returns runtime sync status and persisted latest run summary |
| POST | `/api/sync/manual` | Triggers fire-and-forget manual sync |
| GET | `/api/tickets` | Returns paginated cached tickets with filters |
| GET | `/api/metrics` | Returns KPI and aggregate metrics |
| GET | `/api/network` | Returns node-edge dependency graph |

---

## 1) GET `/api/sync/status`

### Purpose
Return current in-memory sync state and persisted latest run overview.

### Request
No query params.

### Response (200)

```json
{
  "runtime": {
    "is_running": false,
    "trigger": "",
    "started_at": "",
    "manual_requested": false,
    "last_error": ""
  },
  "persisted": {
    "last_run": {
      "run_id": "uuid",
      "trigger_type": "manual",
      "started_at": "2026-06-02T10:00:00+00:00",
      "completed_at": "2026-06-02T10:00:05+00:00",
      "status": "success",
      "links_provided": 1,
      "links_processed": 1,
      "tickets_discovered": 200,
      "tickets_resolved": 198,
      "unresolved_links": 0,
      "errors": 2,
      "error_summary": "..."
    },
    "ticket_count": 198
  }
}
```

---

## 2) POST `/api/sync/manual`

### Purpose
Start manual sync in background (non-blocking).

### Request
No body.

### Response (200)

```json
{
  "accepted": true,
  "queued": false,
  "message": "Manual sync started."
}
```

### Behavior notes
- If another sync is running, manual request is queued and prioritized next.
- Scheduled run requests during active sync are skipped.

---

## 3) GET `/api/tickets`

### Purpose
Fetch cached tickets with optional filters, stable filter metadata, assignee-grouped output, and pagination.

### Query Parameters

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `status` | string[] | No | - | Repeatable or comma-separated exact status filters |
| `assignee` | string[] | No | - | Repeatable or comma-separated exact assignee filters |
| `search` | string | No | - | `LIKE` search on ticket key and summary |
| `board_id` | string | No | - | Filters against `source_links_json` |
| `limit` | int | No | `1000` | Min `1`, max `1000` |
| `offset` | int | No | `0` | Min `0` |

### Frontend Usage Note

- The dashboard UI does not expose a user-editable Rows/page-size control.
- Frontend requests use the maximum supported ticket limit for filtered retrieval.

### Response (200)

```json
{
  "total": 2,
  "limit": 200,
  "offset": 0,
  "filter_options": {
    "statuses": ["Done", "In Progress", "To Do"],
    "assignees": ["Alice", "Bob"]
  },
  "groups": [
    {
      "assignee": "Alice",
      "count": 1,
      "items": []
    },
    {
      "assignee": "Unassigned",
      "count": 1,
      "items": []
    }
  ],
  "items": [
    {
      "ticket_key": "QSYSCLOUD-123",
      "project_key": "QSYSCLOUD",
      "summary": "Sample ticket",
      "status": "In Progress",
      "assignee": "Alice",
      "priority": "High",
      "issue_type": "Bug",
      "reporter": "Bob",
      "updated": "2026-06-02T08:15:00.000+0000",
      "due_date": "2026-06-10",
      "story_points": 3,
      "time_estimate": 3600,
      "time_spent": 1200,
      "source_links": [
        "https://qsc.atlassian.net/jira/software/c/projects/QSYSCLOUD/boards/1863"
      ],
      "dependencies": {
        "blockers": [],
        "blocking": [],
        "other_dependencies": []
      }
    }
  ]
}
```

---

## 4) GET `/api/metrics`

### Purpose
Return dashboard KPI aggregates for the active shared filter scope.

### Request
Optional query params mirror `GET /api/tickets` filter semantics for `status`, `assignee`, `search`, and `board_id`.

### Response (200)

```json
{
  "kpis": {
    "total_active_tickets": 198,
    "open_bug_count": 47,
    "stale_tickets_over_14_days": 12
  },
  "active_by_status": [
    { "status": "To Do", "count": 50 },
    { "status": "In Progress", "count": 120 },
    { "status": "Done", "count": 28 }
  ],
  "dependency_summary": {
    "blockers": 33,
    "inter_team": 18,
    "intra_team": 15
  }
}
```

---

## 5) GET `/api/network`

### Purpose
Return graph payload for dependency visualization scoped to the active shared filters.

### Request
Optional query params mirror `GET /api/tickets` filter semantics for `status`, `assignee`, `search`, and `board_id`.

### Response (200)

```json
{
  "nodes": [
    {
      "id": "QSYSCLOUD-123",
      "ticket_key": "QSYSCLOUD-123",
      "summary": "Sample",
      "status": "In Progress",
      "assignee": "Alice",
      "priority": "High",
      "reporter": "Bob",
      "story_points": 3
    }
  ],
  "edges": [
    {
      "source_ticket": "QSYSCLOUD-123",
      "target_ticket": "QSYSCLOUD-456",
      "relation_name": "Blocks",
      "relation_description": "blocks",
      "dependency_type": "blocking",
      "classification": "inter_team"
    }
  ],
  "counts": {
    "nodes": 1,
    "edges": 1
  }
}
```

---

## Error Behavior

- Validation errors (invalid query params) follow FastAPI default 422 schema.
- Unexpected runtime/database errors return HTTP 500.
- Manual sync endpoint can return `accepted=true` while worker later fails; check `/api/sync/status` for `runtime.last_error`.

## Contract Versioning Notes

- Keep this sheet updated whenever endpoint shape or behavior changes.
- Recommended workflow:
  1. Update this file in same PR/commit as API changes.
  2. Add `Contract Change` section in release notes for frontend consumers.