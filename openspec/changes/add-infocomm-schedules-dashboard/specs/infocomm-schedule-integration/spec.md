## ADDED Requirements

### Requirement: Show selector
The dashboard Infocomm view SHALL provide a selector panel with buttons for "InfoComm India", "InfoComm Asia", and "InfoComm Global". Exactly one show SHALL be active at a time.

#### Scenario: Default show is India
- **WHEN** the user opens the Infocomm tab for the first time
- **THEN** the "InfoComm India" button is highlighted as active and the India schedule is loaded

#### Scenario: Switching shows loads new schedule
- **WHEN** the user clicks a different show button (e.g. "InfoComm Global")
- **THEN** the previous show button becomes inactive, the clicked button becomes active, and the schedule for the selected show is fetched and rendered

### Requirement: Official website link
The Infocomm view SHALL display a link to the official website of the currently selected show, opening in a new browser tab.

#### Scenario: Link updates on show change
- **WHEN** the user selects "InfoComm Asia"
- **THEN** the website link updates to the official InfoComm Asia URL

### Requirement: Date-tab navigation
The schedule panel SHALL group sessions by date and render a date tab for each unique date found in the schedule.

#### Scenario: First date auto-selected
- **WHEN** schedule data is loaded
- **THEN** the first available date tab is automatically selected and its sessions are rendered

#### Scenario: Clicking a date tab filters sessions
- **WHEN** the user clicks a date tab
- **THEN** only the sessions belonging to that date are shown in the session list

### Requirement: Session cards
Each session in the schedule SHALL be rendered as a card showing the session title (linking to the session detail page when a URL is available), duration, location, and description where available.

#### Scenario: Session with all fields
- **WHEN** a session has title, link, duration, location, and description
- **THEN** the card renders all fields with the title as a clickable link that opens in a new tab

#### Scenario: Session with missing optional fields
- **WHEN** a session is missing location or description
- **THEN** those fields are simply omitted from the card without error

### Requirement: Scraper CLI
The `scraper.py` script SHALL accept a `--show` argument with values `india`, `asia`, or `global` (default: `india`). It SHALL scrape the corresponding event website, group sessions by date, resolve relative URLs to absolute, and save JSON and CSV output to `outputs/`.

#### Scenario: Scrape India schedule
- **WHEN** `python scraper.py --show india` is run
- **THEN** `outputs/infocomm_india.json` and `outputs/infocomm_india.csv` are created with session data

#### Scenario: Invalid show argument
- **WHEN** an unrecognised `--show` value is supplied
- **THEN** the script exits with an informative error message

### Requirement: Schedule API endpoint
The backend SHALL expose `GET /api/infocomm/schedule/{show}` where `show` is one of `india`, `asia`, `global`. The endpoint SHALL return cached JSON from `outputs/` instantly when available. If the cache is absent or `?refresh=true` is passed, it SHALL invoke the scraper synchronously and return the fresh result.

#### Scenario: Serve from cache
- **WHEN** `outputs/infocomm_india.json` exists and the request does not include `?refresh=true`
- **THEN** the endpoint returns the cached JSON with a 200 status in under 100ms

#### Scenario: Cache miss triggers scrape
- **WHEN** the cache file does not exist
- **THEN** the scraper is invoked, the output is saved, and the JSON is returned in the response
