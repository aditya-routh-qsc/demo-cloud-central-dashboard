## Why

The QSC dashboard lacks visibility into upcoming InfoComm trade show sessions — the primary industry events where QSC products and integrations are showcased. Teams need a centralized view of session schedules for InfoComm India, Asia, and Global so they can plan attendance and track relevant talks without leaving the dashboard.

## What Changes

- Add a new **Infocomm** tab to the sidebar navigation
- Implement a Playwright-based scraper (`scraper.py`) that fetches session schedules from the official InfoComm event websites (India, Asia, Global)
- Add a backend API endpoint (`GET /api/infocomm/schedule/{show}`) that serves scraped schedule data as JSON, with file-based caching and on-demand scraping fallback
- Implement a two-panel InfoComm view: left panel for show selection and official website link; right panel for date-filtered session cards with titles, durations, locations, and descriptions

## Capabilities

### New Capabilities

- `infocomm-schedule-integration`: Scrape, serve, and display InfoComm session schedules for India, Asia, and Global events within the dashboard

### Modified Capabilities

*(none)*

## Impact

- **New file**: `scraper.py` — Playwright CLI scraper with `--show` argument (`india`, `asia`, `global`)
- **New directory**: `outputs/` — stores pre-scraped JSON/CSV files for caching
- **Modified**: `main.py` — new `/api/infocomm/schedule/{show}` FastAPI route
- **Modified**: `frontend/index.html` — Infocomm tab button and view DOM structure
- **Modified**: `frontend/style.css` — styles for selector, date tabs, and session cards
- **Modified**: `frontend/app.js` — state management, data loading, and rendering for Infocomm
- **Dependencies**: `playwright`, `beautifulsoup4` added to Python dependencies
