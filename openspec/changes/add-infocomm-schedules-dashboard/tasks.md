## 1. Scraper Component

- [x] 1.1 Create `scraper.py` with Playwright-based scraping logic
- [x] 1.2 Add `--show` argument supporting `india`, `asia`, `global` (default: `india`)
- [x] 1.3 Implement dynamic date-tab parsing to group sessions by date
- [x] 1.4 Resolve relative session URLs to absolute using `urllib.parse`
- [x] 1.5 Save scraped output as JSON and CSV under `outputs/` directory

## 2. Backend API

- [x] 2.1 Add `GET /api/infocomm/schedule/{show}` endpoint to `main.py`
- [x] 2.2 Serve pre-scraped JSON from `outputs/infocomm_{show}.json` as cache
- [x] 2.3 Fall back to invoking `scraper.py` subprocess when cache is missing or `?refresh=true` is passed

## 3. Frontend – HTML Structure

- [x] 3.1 Add "Infocomm" tab button to sidebar navigation in `frontend/index.html`
- [x] 3.2 Add `<section id="infocomm" class="view">` with split-panel layout
- [x] 3.3 Add show selector panel with India / Asia / Global buttons and official website link
- [x] 3.4 Add schedule panel with date-tabs container, skeleton loader, and session list container

## 4. Frontend – Styles

- [x] 4.1 Add CSS for `.infocomm-selector-card` and `.infocomm-selector` layout in `frontend/style.css`
- [x] 4.2 Add styles for `.infocomm-btn` with active/hover states
- [x] 4.3 Add styles for `.infocomm-website-link` and link affordances
- [x] 4.4 Add styles for `.infocomm-date-tabs` and `.infocomm-date-tab` with active state
- [x] 4.5 Add styles for `.infocomm-session-card`, `.infocomm-session-title`, `.infocomm-session-meta`, and `.infocomm-session-desc`

## 5. Frontend – JavaScript

- [x] 5.1 Add `infocomm` state object to `state` in `frontend/app.js` (selectedShow, selectedDate, schedule, loading)
- [x] 5.2 Register DOM element refs for InfoComm elements in `el` object
- [x] 5.3 Bind tab click for "infocomm" tab to lazy-load schedule on first activation
- [x] 5.4 Bind show selector button clicks to update `state.infocomm.selectedShow` and reload schedule
- [x] 5.5 Implement `loadInfoCommSchedule()` async function to fetch from `/api/infocomm/schedule/{show}`
- [x] 5.6 Implement `renderInfoCommUI()` to render date tabs, update website link, and render filtered session cards
