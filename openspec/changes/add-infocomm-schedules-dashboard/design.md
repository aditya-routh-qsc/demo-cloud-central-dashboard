## Context

The QSC Cloud Central Dashboard is a FastAPI + vanilla JS single-page application. It already has a tab-based navigation system (`bindTabNavigation`), a sidebar, and established patterns for lazy-loading tab data via `apiGet`. The InfoComm event websites (India, Asia, Global) use a JavaScript-rendered ASP.events platform, requiring a headless browser scraper to extract session data.

## Goals / Non-Goals

**Goals:**
- Add an "Infocomm" sidebar tab and view to the dashboard
- Implement a Playwright-based scraper that extracts sessions for all three show variants
- Provide a FastAPI endpoint that serves cached JSON data or triggers a live scrape
- Render sessions grouped by date with clickable cards linking to session detail pages
- Allow show selection (India / Asia / Global) from the UI

**Non-Goals:**
- Real-time scraping on every page load (intentionally cached; scraper runs on demand or by pre-fetch)
- Authentication with InfoComm systems
- Scraping exhibitor/floor maps or non-session pages
- Server-side push or WebSocket updates for schedule changes

## Decisions

### 1. Playwright over Requests/BeautifulSoup for scraping
The InfoComm schedule pages use JavaScript-rendered tab panels. Static HTML parsing would miss the session data. Playwright's `page.evaluate()` allows waiting for JS-rendered content and extracting it accurately.

*Alternative considered*: Selenium — rejected due to heavier driver setup and slower startup compared to Playwright's async API.

### 2. File-based JSON cache in `outputs/`
Pre-scraped JSON files (`outputs/infocomm_{show}.json`) serve as the primary data source. The backend checks for cache existence and returns it instantly; if the cache is missing or `?refresh=true` is passed, it invokes the scraper subprocess.

*Alternative considered*: SQLite/in-memory cache — rejected for simplicity; JSON files are portable, inspectable, and easy to debug.

### 3. Relative URL resolution using `urllib.parse`
Session links scraped from the page may be relative paths. Using `urllib.parse.urlparse` on the target URL allows dynamically computing the base domain and prefixing relative paths without hardcoding per-show domains.

### 4. Lazy tab loading in the frontend
The InfoComm schedule is only fetched when the user first clicks the Infocomm tab (if `state.infocomm.schedule.length === 0`). This avoids unnecessary API calls on page load and follows the same pattern used for other lazy tabs.

### 5. Date-tab UX for schedule browsing
Sessions are grouped by date. Clicking a date tab filters the visible session cards, mirroring the InfoComm website's own UX pattern and keeping the interface familiar to users who already use the event site.

## Risks / Trade-offs

- **Scraper fragility** → The ASP.events platform may update its HTML structure. Mitigation: use semantic selectors (e.g., `.p-tabs__navigation__title__link`, `.p-tabs__body__content`) rather than positional ones; add error logging.
- **Scraping latency** → First-time scrapes may take 30-60s per show due to Playwright startup + page rendering. Mitigation: pre-scrape via `scraper.py` before deploying; cache is served instantly thereafter.
- **No auto-refresh** → The schedule data can become stale if not re-scraped. Mitigation: expose `?refresh=true` query param on the API endpoint for manual refresh; future work could add a scheduled job.
- **Playwright dependency size** → Playwright with browser binaries adds ~300MB to the environment. Mitigation: acceptable for a developer-facing internal tool; document install steps clearly.
