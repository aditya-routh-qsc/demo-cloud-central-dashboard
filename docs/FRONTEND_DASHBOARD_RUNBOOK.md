# Frontend Dashboard Runbook

This runbook describes how to run and validate the Cloud Central Dashboard frontend.

## Runtime Model

- Backend and frontend are served by the same FastAPI process.
- Frontend entrypoint: `GET /`
- Static assets: `GET /app/*`
- Dashboard data APIs:
  - `GET /api/sync/status`
  - `POST /api/sync/manual`
  - `GET /api/tickets`
  - `GET /api/metrics`
  - `GET /api/network`

## Run Instructions

1. Activate environment.
2. Start API server.
3. Open browser at `http://127.0.0.1:8000/`.

Example commands:

```powershell
.\.venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Smoke Validation

Automated smoke checks:

```powershell
.\.venv\Scripts\python.exe scratch\smoke_frontend_contract.py
```

Expected output:

```text
smoke_ok
```

Manual checks:

1. Global filter persistence
- Apply filters in Overview.
- Switch between views using the left-side navigation.
- Confirm same filter state remains in controls and API-driven values.
- Collapse and reopen advanced filters.
- Confirm the applied filter values remain active while the advanced section is hidden.

2. Multi-select status and assignee filters
- Select multiple statuses, including `Done` when present.
- Confirm URL query state preserves the full selected set.
- Confirm filter dropdowns remain populated from stable dataset options even when paginated results are sparse.

3. Sync trust visibility
- Confirm sync chip is visible at all times in header.
- Click `Sync now` and verify status changes to running/queued/last outcome.

4. Jira deep-links
- From grouped Tickets sections, click `Open` and verify Jira issue URL format.
- In Network, click a node and verify `Open in Jira` appears and works.

5. Mobile summary mode
- Resize browser below 900px width.
- Confirm Overview and Network remain accessible.
- Confirm Network shows summary cards and explicit mobile-mode messaging instead of the interactive graph.
- Confirm dense Metrics/Tickets interactive desktop views remain hidden.

6. Compact shell navigation
- Confirm the main view switcher appears as a left-side navigation rail on desktop.
- Confirm the shell reflows to a compact stacked layout below 900px width.
- Confirm the advanced filter region can be collapsed without clearing selected values.

## Known Limits

- Mobile layout is intentionally read-only summary mode.
- Graph rendering cost increases with very large node/edge sets.
- Jira host is derived from ticket source links when available; fallback host is configured in frontend logic.

## Troubleshooting

1. Frontend root returns 404
- Cause: `frontend/index.html` is missing.
- Fix: restore frontend assets under `frontend/`.

2. Charts or graph not rendering
- Cause: blocked CDN scripts or network restrictions.
- Fix: allow access to jsdelivr CDN or vendor dependencies locally.

3. Sync status not updating
- Cause: backend scheduler or sync worker issue.
- Fix: check `GET /api/sync/status` runtime fields and backend logs.

4. Jira links open wrong domain
- Cause: source links not available/parseable.
- Fix: ensure extracted tickets include source links with the expected Atlassian host.
