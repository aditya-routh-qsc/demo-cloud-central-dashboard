# Project Structure

## Root (runtime-critical)
- `main.py` - FastAPI backend and scheduler
- `services.py` - Jira extraction and dependency parsing
- `database.py` - SQLite schema and persistence helpers
- `config_utils.py` - `.config` loading utilities
- `.env` - Atlassian credentials and runtime env settings
- `.config` - sync interval and database path
- `openspec/` - change artifacts/spec process

## docs/
- `API_CONTRACT_SHEET.md`
- `dashboard_design.md`
- `services_activity_log.md`
- `extract-ticket-dependencies-and-time-metrics.md`
- `openspec_proposal_prompt.txt`

## outputs/
- `dashboard_cache.db` - SQLite runtime cache
- `kanban_ticket_details_response.json` - latest extraction output
- `demo.json` - sample/demo payload

## scratch/
- `tempCodeRunnerFile.py` - temporary editor-generated file

## Notes
- Core app entry points remain in root to avoid breaking imports.
- Generated artifacts are now grouped under `outputs/`.
- Documentation is centralized in `docs/`.
