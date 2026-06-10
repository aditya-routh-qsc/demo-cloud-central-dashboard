"""SQLite connector and persistence helpers for dashboard cache."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

from config_utils import get_database_path, get_team_dropdown_keywords, get_team_visibility_keywords

TRACKED_HISTORY_FIELDS = [
    "status",
    "assignee",
    "due_date",
    "resolution_date",
    "story_points",
    "time_estimate",
    "time_spent",
]

DONE_STATUS_KEYS = {"done", "closed", "resolved"}
IN_PROGRESS_STATUS_KEYS = {"in progress", "in-progress", "in_review", "in review", "testing"}
TEAM_DETAILS_JSON_PATH = Path(__file__).resolve().parent / "inputs" / "team_details.json"
UNMAPPED_TEAM_OPTION = "Unmapped Team"

# Fallback aliases for Jira component labels that do not directly match team names.
DEFAULT_COMPONENT_TEAM_ALIASES: dict[str, list[str]] = {
    "reflect directory": ["Reflect Subdirectory"],
    "reflect infra": ["Infrastructure Team"],
    "cloud services": ["Infrastructure Team"],
    "cloud secops": ["Infrastructure Team"],
}


def _normalize_team_text(value: str) -> str:
    return str(value or "").strip().casefold()


def _canonical_team_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_team_text(value))


def _team_id_from_name(team_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(team_name or "").strip().lower()).strip("-")
    return slug or "unnamed-team"


def _load_team_roster_from_json() -> list[dict[str, Any]]:
    """Load team roster from inputs/team_details.json.
    
    JSON structure is member-centric with nested teams array.
    Transform it to team-centric format (same as CSV output).
    """
    if not TEAM_DETAILS_JSON_PATH.exists():
        return []

    try:
        with TEAM_DETAILS_JSON_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, IOError):
        return []
    
    members_list = data.get("members", [])
    teams_dict: dict[str, dict[str, Any]] = {}
    
    # Transform member-centric JSON to team-centric format
    for member in members_list:
        member_name = member.get("name", "")
        if not member_name:
            continue
        
        member_teams = member.get("teams", [])
        for team_info in member_teams:
            team_name = team_info.get("team", "")
            if not team_name:
                continue
            
            team_id = _team_id_from_name(team_name)
            
            # Initialize team if not seen before
            if team_id not in teams_dict:
                teams_dict[team_id] = {
                    "team_id": team_id,
                    "team_name": team_name,
                    "pod": team_info.get("pod", ""),
                    "description": "",
                    "members": [],
                }
            
            # Add member to team
            teams_dict[team_id]["members"].append({
                "display_name": member_name,
                "role": team_info.get("role") or "",
                "skillset": member.get("skillset") or "",
                "location": member.get("location") or "",
                "contractor": member.get("contractor") or "",
                "notes": member.get("notes") or "",
            })
    
    # Convert to list and deduplicate
    teams = list(teams_dict.values())
    
    # De-duplicate by normalized team name
    deduped: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for team in teams:
        normalized_name = _normalize_team_text(team.get("team_name", ""))
        if not normalized_name or normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)
        deduped.append(team)
    
    return deduped


def _load_team_roster_source() -> list[dict[str, Any]]:
    """Load team roster from inputs/team_details.json."""
    return _load_team_roster_from_json()


def _load_component_team_aliases() -> dict[str, list[str]]:
    """Return normalized/canonical component name aliases mapped to team names."""
    aliases: dict[str, list[str]] = {}

    # Seed with built-in aliases first.
    for component_name, team_names in DEFAULT_COMPONENT_TEAM_ALIASES.items():
        for key in (_normalize_team_text(component_name), _canonical_team_text(component_name)):
            if not key:
                continue
            aliases.setdefault(key, [])
            for team_name in team_names:
                if team_name not in aliases[key]:
                    aliases[key].append(team_name)

    if not TEAM_DETAILS_JSON_PATH.exists():
        return aliases

    try:
        with TEAM_DETAILS_JSON_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, IOError):
        return {}

    component_rows = data.get("components", []) if isinstance(data, dict) else []
    for row in component_rows:
        if not isinstance(row, dict):
            continue
        component_name = str(row.get("name") or "").strip()
        mapped_team_name = str(row.get("team") or "").strip()
        if not component_name or not mapped_team_name:
            continue
        for key in (_normalize_team_text(component_name), _canonical_team_text(component_name)):
            if not key:
                continue
            aliases.setdefault(key, [])
            if mapped_team_name not in aliases[key]:
                aliases[key].append(mapped_team_name)

    return aliases



KNOWN_ASSIGNEE_MAPPING = {
    "anna, sureshkumar": "sureshkumar anna",
    "ashok, ananya": "ananya a",
    "bandi, vishnu t": "vishnu bandi",
    "chauhan, akash": "akash chauhan",
    "dang, minh t": "minh dang",
    "derangula, sivaprasad": "sivaprasad derangula",
    "hessler, christian j": "christian hessler",
    "jain, ruchika": "ruchikajain",
    "johnson, dane a": "dane johnson*",
    "karmalkar, shubham s": "shubam karmalkar",
    "kumar, shashi": "shashi kumar",
    "lizunov, roman lizunov -ctr": "roman luzinov",
    "madhavi, giriboina": "madhavi g",
    "mazurenko, vitalii mazurenko -ctr": "vitalii mazurenko",
    "mohanty, abinash": "abinash",
    "mukane, fawaz a": "fawaz mukane",
    "rakshit, saswata": "saswata r",
    "singh, nishant -ctr": "nishant singh",
    "singh, pawan k": "pawan singh",
    "sinha, ashutosh kumar": "ashutosh sinha",
    "surbhat, abhishek": "abhishek surbhat",
    "walekar, shrutika": "shrutika walekar",
}


def clean_for_fallback(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"-CTR", "", name, flags=re.I)
    name = name.replace("*", "")
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_assignee_to_member(db_assignee: str) -> str | None:
    db_assignee_clean = str(db_assignee or "").strip().lower()

    if db_assignee_clean in KNOWN_ASSIGNEE_MAPPING:
        return KNOWN_ASSIGNEE_MAPPING[db_assignee_clean]

    all_members = []
    for team in load_team_roster():
        for member in (team.get("members") or []):
            csv_n = str(member.get("display_name") or "").strip()
            if csv_n:
                all_members.append(csv_n)

    for csv_n in all_members:
        if csv_n.lower() == db_assignee_clean:
            return csv_n

    parts = [p.strip() for p in db_assignee_clean.split(",")]
    if len(parts) == 2:
        reversed_name = f"{parts[1]} {parts[0]}"
        for csv_n in all_members:
            if csv_n.lower() == reversed_name:
                return csv_n

    cleaned_db = clean_for_fallback(db_assignee_clean)
    cleaned_db_reversed = ""
    if len(parts) == 2:
        cleaned_db_reversed = clean_for_fallback(f"{parts[1]} {parts[0]}")
    for csv_n in all_members:
        cleaned_csv = clean_for_fallback(csv_n)
        if cleaned_csv == cleaned_db or (cleaned_db_reversed and cleaned_csv == cleaned_db_reversed):
            return csv_n

    db_tokens = [w for w in re.sub(r"[^a-z]", " ", db_assignee_clean).split() if w not in ("ctr", "ds")]
    for csv_n in all_members:
        csv_tokens = [w for w in re.sub(r"[^a-z]", " ", csv_n.lower()).split() if w not in ("ctr", "ds")]
        if not db_tokens or not csv_tokens:
            continue
        long_shared = [w for w in db_tokens if w in csv_tokens and len(w) >= 4]
        if long_shared:
            return csv_n

    return None


def _member_names_for_team_values(team_values: list[str]) -> list[str]:
    roster = load_team_roster(team_filters=team_values)
    matching_csv_names = {
        str(member.get("display_name") or "").strip().casefold()
        for team in roster
        for member in (team.get("members") or [])
        if str(member.get("display_name") or "").strip()
    }

    with get_connection() as conn:
        try:
            rows = conn.execute("SELECT DISTINCT assignee FROM tickets_current WHERE assignee IS NOT NULL AND assignee != ''").fetchall()
            db_assignees = [row["assignee"] for row in rows]
        except sqlite3.OperationalError:
            db_assignees = []

    matched_db_names: set[str] = set()
    for db_assignee in db_assignees:
        matched_csv = match_assignee_to_member(db_assignee)
        if matched_csv and matched_csv.casefold() in matching_csv_names:
            matched_db_names.add(db_assignee.strip().lower())

    for csv_n in matching_csv_names:
        matched_db_names.add(csv_n)

    return sorted(list(matched_db_names))


def _get_primary_team_for_assignee(assignee_name: str) -> tuple[str, str]:
    """Return (team_id, team_name) for assignee's primary team, or ("", "") if not found.
    
    Primary team is the first team listed in the member's teams array in the JSON.
    """
    if not assignee_name or not str(assignee_name or "").strip():
        return "", ""
    
    assignee_lower = str(assignee_name).strip().casefold()
    
    # Load JSON directly to find member's primary team
    if not TEAM_DETAILS_JSON_PATH.exists():
        return "", ""

    try:
        with TEAM_DETAILS_JSON_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, IOError):
        return "", ""
    
    members_list = data.get("members", [])
    for member in members_list:
        member_name = str(member.get("name") or "").strip()
        if member_name.casefold() == assignee_lower:
            # Found the member - get their first (primary) team
            member_teams = member.get("teams", [])
            if member_teams and isinstance(member_teams, list) and len(member_teams) > 0:
                primary_team = member_teams[0]
                team_name = str(primary_team.get("team") or "").strip()
                if team_name:
                    team_id = _team_id_from_name(team_name)
                    return team_id, team_name
            break
    
    return "", ""


def _resolve_teams_from_components(components: Any) -> list[tuple[str, str]]:
    """Resolve one or more teams from Jira component names."""
    if not isinstance(components, list) or not components:
        return []

    component_names = [
        str(component.get("name") or "") if isinstance(component, dict) else str(component or "")
        for component in components
    ]
    component_names = [name.strip() for name in component_names if str(name or "").strip()]
    if not component_names:
        return []

    roster = load_team_roster()
    teams_by_exact_name = {
        _normalize_team_text(team.get("team_name", "")): (
            str(team.get("team_id") or "").strip(),
            str(team.get("team_name") or "").strip(),
        )
        for team in roster
        if str(team.get("team_id") or "").strip() and str(team.get("team_name") or "").strip()
    }
    teams_by_canonical_name = {
        _canonical_team_text(team.get("team_name", "")): (
            str(team.get("team_id") or "").strip(),
            str(team.get("team_name") or "").strip(),
        )
        for team in roster
        if str(team.get("team_id") or "").strip() and str(team.get("team_name") or "").strip()
    }
    aliases = _load_component_team_aliases()
    resolved: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _append(team_id: str, team_name: str) -> None:
        value = (str(team_id or "").strip(), str(team_name or "").strip())
        if not value[0] or not value[1]:
            return
        if value in seen:
            return
        seen.add(value)
        resolved.append(value)

    for component_name in component_names:
        normalized_component_name = _normalize_team_text(component_name)
        canonical_component_name = _canonical_team_text(component_name)

        alias_targets = aliases.get(normalized_component_name, []) + aliases.get(canonical_component_name, [])
        for team_name in alias_targets:
            matched = teams_by_exact_name.get(_normalize_team_text(team_name))
            if matched:
                _append(*matched)

        matched = teams_by_exact_name.get(normalized_component_name)
        if matched:
            _append(*matched)
            continue

        matched = teams_by_canonical_name.get(canonical_component_name)
        if matched:
            _append(*matched)
            continue

        for team in roster:
            team_name = str(team.get("team_name") or "").strip()
            team_id = str(team.get("team_id") or "").strip()
            if not team_name or not team_id:
                continue
            team_name_norm = _normalize_team_text(team_name)
            team_name_canonical = _canonical_team_text(team_name)
            if not team_name_norm:
                continue
            if (
                normalized_component_name in team_name_norm
                or team_name_norm in normalized_component_name
                or canonical_component_name in team_name_canonical
                or team_name_canonical in canonical_component_name
            ):
                _append(team_id, team_name)

    return resolved


def _get_team_from_components(components: Any) -> tuple[str, str]:
    """Resolve primary team from Jira components, preserving backward compatibility."""
    resolved = _resolve_teams_from_components(components)
    return resolved[0] if resolved else ("", "")


def _resolve_ticket_teams(ticket: dict[str, Any]) -> list[tuple[str, str]]:
    """Resolve ticket teams with priority: all components first, assignee fallback second."""
    from_components = _resolve_teams_from_components(ticket.get("components"))
    if from_components:
        return from_components

    assignee_team_id, assignee_team_name = _get_primary_team_for_assignee(ticket.get("assignee", ""))
    if assignee_team_id and assignee_team_name:
        return [(assignee_team_id, assignee_team_name)]

    return []


def _resolve_ticket_team(ticket: dict[str, Any]) -> tuple[str, str]:
    """Resolve primary ticket team with priority: components first, assignee fallback second."""
    resolved = _resolve_ticket_teams(ticket)
    return resolved[0] if resolved else ("", "")


def find_misclassified_unmapped_tickets(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return tickets marked unmapped that can actually be mapped from components.

    Input tickets should contain: ticket_key, team_name/team_id (optional), and components.
    """
    misclassified: list[dict[str, Any]] = []
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        team_name = _normalize_team_text(ticket.get("team_name", ""))
        team_id = _normalize_team_text(ticket.get("team_id", ""))
        is_currently_unmapped = not team_name and not team_id
        if team_name == _normalize_team_text(UNMAPPED_TEAM_OPTION):
            is_currently_unmapped = True
        if not is_currently_unmapped:
            continue

        resolved_teams = _resolve_teams_from_components(ticket.get("components"))
        if not resolved_teams:
            continue

        misclassified.append(
            {
                "ticket_key": str(ticket.get("ticket_key") or "").strip(),
                "resolved_teams": [
                    {"team_id": team_id, "team_name": team_name}
                    for team_id, team_name in resolved_teams
                ],
                "components": ticket.get("components") if isinstance(ticket.get("components"), list) else [],
            }
        )

    return misclassified


def _member_to_team_lookup() -> dict[str, dict[str, str]]:

    lookup: dict[str, dict[str, str]] = {}
    for team in load_team_roster():
        team_id = str(team.get("team_id") or "").strip()
        team_name = str(team.get("team_name") or "").strip()
        for member in (team.get("members") or []):
            csv_name = str(member.get("display_name") or "").strip()
            if not csv_name:
                continue
            lookup[csv_name.casefold()] = {"team_id": team_id, "team_name": team_name}

    with get_connection() as conn:
        try:
            rows = conn.execute("SELECT DISTINCT assignee FROM tickets_current WHERE assignee IS NOT NULL AND assignee != ''").fetchall()
            db_assignees = [row["assignee"] for row in rows]
        except sqlite3.OperationalError:
            db_assignees = []

    for db_assignee in db_assignees:
        matched_csv = match_assignee_to_member(db_assignee)
        if matched_csv:
            csv_meta = lookup.get(matched_csv.casefold())
            if csv_meta:
                lookup[db_assignee.strip().casefold()] = csv_meta

    return lookup


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield sqlite connection with row access by column name."""
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _ensure_column_exists(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    """Add a missing sqlite column for backward-compatible schema upgrades."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {str(row[1]) for row in rows}
    if column_name in existing_columns:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db() -> None:
    """Create all persistence tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_runs (
                run_id TEXT PRIMARY KEY,
                trigger_type TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                links_provided INTEGER NOT NULL DEFAULT 0,
                links_processed INTEGER NOT NULL DEFAULT 0,
                tickets_discovered INTEGER NOT NULL DEFAULT 0,
                tickets_resolved INTEGER NOT NULL DEFAULT 0,
                unresolved_links INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                error_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS tickets_current (
                ticket_key TEXT PRIMARY KEY,
                project_key TEXT,
                summary TEXT,
                issue_type TEXT,
                status TEXT,
                priority TEXT,
                assignee TEXT,
                reporter TEXT,
                report_date TEXT,
                due_date TEXT,
                resolution_date TEXT,
                updated TEXT,
                story_points REAL,
                time_original_estimate INTEGER,
                time_estimate INTEGER,
                time_spent INTEGER,
                source_links_json TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                last_seen_run_id TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ticket_dependencies_current (
                source_ticket_key TEXT NOT NULL,
                target_ticket_key TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                relation_name TEXT,
                relation_description TEXT,
                direction TEXT,
                classification TEXT,
                source_project_key TEXT,
                target_project_key TEXT,
                target_status TEXT,
                last_seen_run_id TEXT NOT NULL,
                PRIMARY KEY (source_ticket_key, target_ticket_key, dependency_type, relation_name, direction)
            );

            CREATE TABLE IF NOT EXISTS ticket_history_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_key TEXT NOT NULL,
                run_id TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT
            );

            CREATE TABLE IF NOT EXISTS unresolved_link_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                board_link TEXT NOT NULL,
                board_id TEXT,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sync_runtime_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets_current(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_assignee ON tickets_current(assignee);
            CREATE INDEX IF NOT EXISTS idx_tickets_updated ON tickets_current(updated);
            CREATE INDEX IF NOT EXISTS idx_deps_source ON ticket_dependencies_current(source_ticket_key);
            CREATE INDEX IF NOT EXISTS idx_deps_target ON ticket_dependencies_current(target_ticket_key);
            CREATE INDEX IF NOT EXISTS idx_history_ticket ON ticket_history_log(ticket_key, changed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_runs_started ON sync_runs(started_at DESC);
            """
        )
        conn.commit()
        
        # Ensure team columns exist (for ticket ownership by team)
        _ensure_column_exists(conn, "tickets_current", "team_id", "team_id TEXT")
        _ensure_column_exists(conn, "tickets_current", "team_name", "team_name TEXT")
        _ensure_column_exists(conn, "tickets_current", "team_ids_json", "team_ids_json TEXT")
        _ensure_column_exists(conn, "tickets_current", "team_names_json", "team_names_json TEXT")
        conn.commit()


def _to_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def _project_key(ticket_key: str) -> str:
    return ticket_key.split("-")[0] if "-" in ticket_key else ""


def _extract_board_id_from_link(board_link: str) -> str:
    path = urlparse(board_link).path
    parts = [part for part in path.split("/") if part]
    if "boards" in parts:
        idx = parts.index("boards")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def _load_existing_tickets(conn: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    rows = conn.execute("SELECT * FROM tickets_current").fetchall()
    return {str(row["ticket_key"]): row for row in rows}


def _insert_ticket_history(
    conn: sqlite3.Connection,
    run_id: str,
    now_iso: str,
    ticket_key: str,
    previous: sqlite3.Row | None,
    current_ticket: dict[str, Any],
) -> None:
    if previous is None:
        conn.execute(
            """
            INSERT INTO ticket_history_log(ticket_key, run_id, changed_at, field_name, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_key, run_id, now_iso, "created", None, current_ticket.get("status", "")),
        )
        return

    for field_name in TRACKED_HISTORY_FIELDS:
        old_value = previous[field_name] if field_name in previous.keys() else None
        new_value = current_ticket.get(field_name)
        if str(old_value) != str(new_value):
            conn.execute(
                """
                INSERT INTO ticket_history_log(ticket_key, run_id, changed_at, field_name, old_value, new_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ticket_key, run_id, now_iso, field_name, str(old_value) if old_value is not None else None, str(new_value) if new_value is not None else None),
            )


def persist_extraction_result(payload: dict[str, Any], trigger_type: str) -> str:
    """Persist extraction payload into SQLite and return generated run id."""
    init_db()
    run_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    counts = payload.get("counts", {}) if isinstance(payload.get("counts"), dict) else {}
    partial_errors = payload.get("partial_errors", []) if isinstance(payload.get("partial_errors"), list) else []

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_runs(
                run_id, trigger_type, started_at, completed_at, status,
                links_provided, links_processed, tickets_discovered, tickets_resolved,
                unresolved_links, errors, error_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                trigger_type,
                now_iso,
                now_iso,
                "partial" if partial_errors else "success",
                int(counts.get("links_provided", 0)),
                int(counts.get("links_processed", 0)),
                int(counts.get("tickets_discovered", 0)),
                int(counts.get("tickets_resolved", 0)),
                int(counts.get("unresolved_links", 0)),
                int(counts.get("errors", 0)),
                "\n".join(partial_errors[:5]) if partial_errors else None,
            ),
        )

        conn.execute("DELETE FROM ticket_dependencies_current")

        existing = _load_existing_tickets(conn)
        results = payload.get("results", []) if isinstance(payload.get("results"), list) else []

        for ticket in results:
            if not isinstance(ticket, dict):
                continue
            ticket_key = str(ticket.get("ticket_key", "")).strip()
            if not ticket_key:
                continue

            _insert_ticket_history(
                conn=conn,
                run_id=run_id,
                now_iso=now_iso,
                ticket_key=ticket_key,
                previous=existing.get(ticket_key),
                current_ticket=ticket,
            )

            # Resolve one or more teams from components first; fallback to assignee mapping.
            resolved_teams = _resolve_ticket_teams(ticket)
            team_ids = [team_id for team_id, _team_name in resolved_teams if str(team_id or "").strip()]
            team_names = [team_name for _team_id, team_name in resolved_teams if str(team_name or "").strip()]
            team_id = team_ids[0] if team_ids else ""
            team_name = team_names[0] if team_names else ""

            conn.execute(
                """
                INSERT INTO tickets_current(
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name, team_ids_json, team_names_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_key) DO UPDATE SET
                    project_key=excluded.project_key,
                    summary=excluded.summary,
                    issue_type=excluded.issue_type,
                    status=excluded.status,
                    priority=excluded.priority,
                    assignee=excluded.assignee,
                    reporter=excluded.reporter,
                    report_date=excluded.report_date,
                    due_date=excluded.due_date,
                    resolution_date=excluded.resolution_date,
                    updated=excluded.updated,
                    story_points=excluded.story_points,
                    time_original_estimate=excluded.time_original_estimate,
                    time_estimate=excluded.time_estimate,
                    time_spent=excluded.time_spent,
                    source_links_json=excluded.source_links_json,
                    dependencies_json=excluded.dependencies_json,
                    last_seen_run_id=excluded.last_seen_run_id,
                    updated_at=excluded.updated_at,
                    team_id=excluded.team_id,
                    team_name=excluded.team_name,
                    team_ids_json=excluded.team_ids_json,
                    team_names_json=excluded.team_names_json
                """,
                (
                    ticket_key,
                    _project_key(ticket_key),
                    ticket.get("summary", ""),
                    ticket.get("issue_type", ""),
                    ticket.get("status", ""),
                    ticket.get("priority", ""),
                    ticket.get("assignee", ""),
                    ticket.get("reporter", ""),
                    ticket.get("report_date", ""),
                    ticket.get("due_date"),
                    ticket.get("resolution_date"),
                    ticket.get("updated", ""),
                    ticket.get("story_points"),
                    ticket.get("time_original_estimate"),
                    ticket.get("time_estimate"),
                    ticket.get("time_spent"),
                    _to_json(ticket.get("source_links", [])),
                    _to_json(ticket.get("dependencies", {})),
                    run_id,
                    now_iso,
                    team_id,
                    team_name,
                    _to_json(team_ids),
                    _to_json(team_names),
                ),
            )

            dependencies = ticket.get("dependencies", {}) if isinstance(ticket.get("dependencies"), dict) else {}
            for dependency_type in ("blockers", "blocking", "other_dependencies"):
                dep_rows = dependencies.get(dependency_type, [])
                if not isinstance(dep_rows, list):
                    continue
                for dep in dep_rows:
                    if not isinstance(dep, dict):
                        continue
                    target_key = str(dep.get("ticket_key", "")).strip()
                    if not target_key:
                        continue
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO ticket_dependencies_current(
                            source_ticket_key, target_ticket_key, dependency_type,
                            relation_name, relation_description, direction, classification,
                            source_project_key, target_project_key, target_status, last_seen_run_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ticket_key,
                            target_key,
                            dependency_type,
                            dep.get("relation_name", ""),
                            dep.get("relation_description", ""),
                            dep.get("direction", ""),
                            dep.get("classification", ""),
                            _project_key(ticket_key),
                            _project_key(target_key),
                            dep.get("status", ""),
                            run_id,
                        ),
                    )

        unresolved = payload.get("unresolved_links", []) if isinstance(payload.get("unresolved_links"), list) else []
        for unresolved_link in unresolved:
            if not isinstance(unresolved_link, dict):
                continue
            board_link = str(unresolved_link.get("board_link", "")).strip()
            if not board_link:
                continue
            conn.execute(
                """
                INSERT INTO unresolved_link_events(run_id, board_link, board_id, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    board_link,
                    unresolved_link.get("board_id") or _extract_board_id_from_link(board_link),
                    str(unresolved_link.get("reason", "unknown")),
                    now_iso,
                ),
            )

        conn.commit()

    return run_id


def read_sync_overview() -> dict[str, Any]:
    """Return latest run summary and basic counts for status endpoint."""
    init_db()
    with get_connection() as conn:
        latest = conn.execute(
            """
            SELECT run_id, trigger_type, started_at, completed_at, status,
                   links_provided, links_processed, tickets_discovered, tickets_resolved,
                   unresolved_links, errors, error_summary
            FROM sync_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()

        ticket_count = conn.execute("SELECT COUNT(*) AS count FROM tickets_current").fetchone()["count"]

    if not latest:
        return {
            "last_run": None,
            "ticket_count": ticket_count,
        }

    return {
        "last_run": {
            "run_id": latest["run_id"],
            "trigger_type": latest["trigger_type"],
            "started_at": latest["started_at"],
            "completed_at": latest["completed_at"],
            "status": latest["status"],
            "links_provided": latest["links_provided"],
            "links_processed": latest["links_processed"],
            "tickets_discovered": latest["tickets_discovered"],
            "tickets_resolved": latest["tickets_resolved"],
            "unresolved_links": latest["unresolved_links"],
            "errors": latest["errors"],
            "error_summary": latest["error_summary"],
        },
        "ticket_count": ticket_count,
    }


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
    table_alias: str = "",
) -> tuple[str, list[Any]]:
    prefix = f"{table_alias}." if table_alias else ""
    where_parts: list[str] = []
    params: list[Any] = []

    _append_exact_multi_filter(where_parts, params, f"{prefix}status", statuses)
    _append_exact_multi_filter(where_parts, params, f"{prefix}assignee", assignees)
    _append_exclusion_multi_filter(where_parts, params, f"{prefix}status", excluded_statuses)
    _append_exclusion_multi_filter(where_parts, params, f"{prefix}assignee", excluded_assignees)

    if search:
        where_parts.append(f"({prefix}ticket_key LIKE ? OR {prefix}summary LIKE ?)")
        like_value = f"%{search}%"
        params.extend([like_value, like_value])

    if board_id:
        where_parts.append(f"{prefix}source_links_json LIKE ?")
        params.append(f"%/boards/{board_id}%")

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    return where_clause, params


def _extend_where_clause(where_clause: str, extra_condition: str) -> str:
    if where_clause:
        return f"{where_clause} AND {extra_condition}"
    return f"WHERE {extra_condition}"


def _append_team_filter_exists(
    where_parts: list[str],
    params: list[Any],
    assignee_sql: str,
    team_values: list[str],
) -> None:
    """Filter tickets by team ownership, with fallback for legacy rows.

    Primary path uses ticket.team_id / ticket.team_name.
    Fallback path uses assignee membership for legacy rows where team fields are blank.
    """
    if not team_values:
        return

    # Normalize team filter values
    normalized_filters = {_normalize_team_text(value) for value in team_values if str(value or "").strip()}
    if not normalized_filters:
        return

    include_unmapped = _normalize_team_text(UNMAPPED_TEAM_OPTION) in normalized_filters
    normalized_filters.discard(_normalize_team_text(UNMAPPED_TEAM_OPTION))
    team_values_without_unmapped = [
        value
        for value in team_values
        if _normalize_team_text(value) != _normalize_team_text(UNMAPPED_TEAM_OPTION)
    ]

    # Get normalized team IDs and names from roster
    team_ids: set[str] = set()
    team_names: set[str] = set()
    for team in load_team_roster():
        team_id = str(team.get("team_id") or "").strip()
        team_name = str(team.get("team_name") or "").strip()
        if _normalize_team_text(team_id) in normalized_filters or _normalize_team_text(team_name) in normalized_filters:
            if team_id:
                team_ids.add(team_id.casefold())
            if team_name:
                team_names.add(team_name.casefold())
    
    if not team_ids and not team_names and not include_unmapped:
        # No matching teams found, return no results
        where_parts.append("1 = 0")
        return

    # Filter by team_id/team_name (including multi-team JSON fields), with legacy assignee fallback.
    team_ids_sorted = sorted(team_ids)
    team_names_sorted = sorted(team_names)
    no_team_assignment_condition = (
        "((tc.team_id IS NULL OR tc.team_id = '') "
        "AND (tc.team_name IS NULL OR tc.team_name = '') "
        "AND (tc.team_ids_json IS NULL OR tc.team_ids_json = '' OR tc.team_ids_json = '[]') "
        "AND (tc.team_names_json IS NULL OR tc.team_names_json = '' OR tc.team_names_json = '[]'))"
    )

    team_conditions: list[str] = []
    team_condition_params: list[Any] = []
    if team_ids_sorted:
        team_id_placeholders = ", ".join("?" for _ in team_ids_sorted)
        team_conditions.append(f"LOWER(TRIM(tc.team_id)) IN ({team_id_placeholders})")
        team_condition_params.extend(team_ids_sorted)
        for team_id in team_ids_sorted:
            team_conditions.append("tc.team_ids_json LIKE ?")
            team_condition_params.append(f'%"{team_id}"%')
    if team_names_sorted:
        team_name_placeholders = ", ".join("?" for _ in team_names_sorted)
        team_conditions.append(f"LOWER(TRIM(tc.team_name)) IN ({team_name_placeholders})")
        team_condition_params.extend(team_names_sorted)
        for team_name in team_names_sorted:
            team_conditions.append("tc.team_names_json LIKE ?")
            team_condition_params.append(f'%"{team_name}"%')
    base_team_condition = " OR ".join(team_conditions) if team_conditions else "1 = 0"

    member_names_sorted = _member_names_for_team_values(team_values_without_unmapped) if team_values_without_unmapped else []
    if member_names_sorted:
        member_placeholders = ", ".join("?" for _ in member_names_sorted)
        legacy_member_condition = (
            f"({no_team_assignment_condition} "
            f"AND LOWER(TRIM({assignee_sql})) IN ({member_placeholders}))"
        )
        if include_unmapped:
            all_mapped_assignees = _member_names_for_team_values([])
            if all_mapped_assignees:
                mapped_placeholders = ", ".join("?" for _ in all_mapped_assignees)
                unmapped_condition = (
                    f"({no_team_assignment_condition} "
                    f"AND ({assignee_sql} IS NULL OR TRIM({assignee_sql}) = '' "
                    f"OR LOWER(TRIM({assignee_sql})) NOT IN ({mapped_placeholders})))"
                )
                combined_condition = f"({base_team_condition} OR {legacy_member_condition} OR {unmapped_condition})"
                where_parts.append(combined_condition)
                params.extend(team_condition_params)
                params.extend(member_names_sorted)
                params.extend(all_mapped_assignees)
                return
            unmapped_condition = (
                f"({no_team_assignment_condition})"
            )
            combined_condition = f"({base_team_condition} OR {legacy_member_condition} OR {unmapped_condition})"
            where_parts.append(combined_condition)
            params.extend(team_condition_params)
            params.extend(member_names_sorted)
            return

        where_parts.append(f"({base_team_condition} OR {legacy_member_condition})")
        params.extend(team_condition_params)
        params.extend(member_names_sorted)
        return

    if include_unmapped:
        all_mapped_assignees = _member_names_for_team_values([])
        if all_mapped_assignees:
            mapped_placeholders = ", ".join("?" for _ in all_mapped_assignees)
            unmapped_condition = (
                f"({no_team_assignment_condition} "
                f"AND ({assignee_sql} IS NULL OR TRIM({assignee_sql}) = '' "
                f"OR LOWER(TRIM({assignee_sql})) NOT IN ({mapped_placeholders})))"
            )
            where_parts.append(f"({base_team_condition} OR {unmapped_condition})")
            params.extend(team_condition_params)
            params.extend(all_mapped_assignees)
            return
        where_parts.append(f"({base_team_condition} OR {no_team_assignment_condition})")
        params.extend(team_condition_params)
        return

    where_parts.append(f"({base_team_condition})")
    params.extend(team_condition_params)


def _status_bucket(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in DONE_STATUS_KEYS:
        return "done"
    if normalized in IN_PROGRESS_STATUS_KEYS:
        return "in_progress"
    return "todo"


def _ticket_from_row(row: sqlite3.Row) -> dict[str, Any]:
    source_links = json.loads(row["source_links_json"] or "[]")
    dependencies = json.loads(row["dependencies_json"] or "{}")
    return {
        "ticket_key": row["ticket_key"],
        "project_key": row["project_key"],
        "summary": row["summary"],
        "status": row["status"],
        "assignee": row["assignee"],
        "priority": row["priority"],
        "issue_type": row["issue_type"],
        "reporter": row["reporter"],
        "updated": row["updated"],
        "due_date": row["due_date"],
        "story_points": row["story_points"],
        "time_estimate": row["time_estimate"],
        "time_spent": row["time_spent"],
        "source_links": source_links,
        "dependencies": dependencies,
        "team_id": row["team_id"] if "team_id" in row.keys() else None,
        "team_name": row["team_name"] if "team_name" in row.keys() else None,
        "team_ids": json.loads(row["team_ids_json"] or "[]") if "team_ids_json" in row.keys() else [],
        "team_names": json.loads(row["team_names_json"] or "[]") if "team_names_json" in row.keys() else [],
    }


def load_filter_options(
    search: str | None,
    board_id: str | None,
    statuses: list[str] | None = None,
    assignees: list[str] | None = None,
    excluded_statuses: list[str] | None = None,
    excluded_assignees: list[str] | None = None,
    teams: list[str] | None = None,
) -> dict[str, list[str]]:
    """Return status/assignee options from filtered ticket scope."""
    statuses = statuses or []
    assignees = assignees or []
    excluded_statuses = excluded_statuses or []
    excluded_assignees = excluded_assignees or []
    teams = teams or []

    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    query_params = list(params)
    _append_team_filter_exists(where_parts, query_params, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    # Team dropdown options should come from stored tickets and ignore active team filter,
    # so users can still see/select other valid teams.
    team_scope_where_clause = where_clause
    team_scope_params = list(params)

    with get_connection() as conn:
        status_rows = conn.execute(
            f"""
            SELECT DISTINCT tc.status
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.status COLLATE NOCASE ASC
            """,
            query_params,
        ).fetchall()

        team_rows = conn.execute(
            f"""
            SELECT DISTINCT tc.team_id, tc.team_name, tc.team_ids_json, tc.team_names_json, tc.assignee
            FROM tickets_current tc
            {team_scope_where_clause}
            """,
            team_scope_params,
        ).fetchall()

        assignee_rows = conn.execute(
            f"""
            SELECT DISTINCT tc.assignee
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.assignee COLLATE NOCASE ASC
            """,
            query_params,
        ).fetchall()

    statuses = [str(row["status"]).strip() for row in status_rows if str(row["status"] or "").strip()]
    assignees = [
        str(row["assignee"]).strip()
        for row in assignee_rows
        if str(row["assignee"] or "").strip()
    ]

    roster = load_team_roster()
    team_id_to_name = {
        str(team.get("team_id") or "").strip().casefold(): str(team.get("team_name") or "").strip()
        for team in roster
        if str(team.get("team_id") or "").strip() and str(team.get("team_name") or "").strip()
    }
    member_to_team_name = {
        str(member.get("display_name") or "").strip().casefold(): str(team.get("team_name") or "").strip()
        for team in roster
        for member in (team.get("members") or [])
        if str(member.get("display_name") or "").strip() and str(team.get("team_name") or "").strip()
    }

    valid_team_names: set[str] = set()
    has_unmapped_tickets = False
    for row in team_rows:
        team_name = str(row["team_name"] or "").strip()
        if team_name:
            valid_team_names.add(team_name)

        team_id = str(row["team_id"] or "").strip().casefold()
        if team_id and team_id in team_id_to_name:
            valid_team_names.add(team_id_to_name[team_id])

        team_names_json = str(row["team_names_json"] or "").strip() if "team_names_json" in row.keys() else ""
        if team_names_json:
            try:
                for value in json.loads(team_names_json):
                    normalized = str(value or "").strip()
                    if normalized:
                        valid_team_names.add(normalized)
            except json.JSONDecodeError:
                pass

        team_ids_json = str(row["team_ids_json"] or "").strip() if "team_ids_json" in row.keys() else ""
        if team_ids_json:
            try:
                for value in json.loads(team_ids_json):
                    normalized = str(value or "").strip().casefold()
                    if normalized and normalized in team_id_to_name:
                        valid_team_names.add(team_id_to_name[normalized])
            except json.JSONDecodeError:
                pass

        if team_name or team_id or team_names_json or team_ids_json:
            continue

        assignee = str(row["assignee"] or "").strip()
        if not assignee:
            has_unmapped_tickets = True
            continue
        matched_member = match_assignee_to_member(assignee)
        if not matched_member:
            has_unmapped_tickets = True
            continue
        mapped_team = member_to_team_name.get(str(matched_member).strip().casefold())
        if mapped_team:
            valid_team_names.add(mapped_team)
        else:
            has_unmapped_tickets = True

    if has_unmapped_tickets:
        valid_team_names.add(UNMAPPED_TEAM_OPTION)

    allowed_dropdown_team_names = {
        str(team.get("team_name") or "").strip()
        for team in load_team_roster_for_dropdown()
        if str(team.get("team_name") or "").strip()
    }
    dropdown_keywords = [
        _normalize_team_text(value)
        for value in get_team_dropdown_keywords()
        if _normalize_team_text(value)
    ]
    include_unmapped_via_keyword = any(
        keyword in _normalize_team_text(UNMAPPED_TEAM_OPTION)
        for keyword in dropdown_keywords
    )
    if allowed_dropdown_team_names:
        team_names = [name for name in valid_team_names if name in allowed_dropdown_team_names]
        if UNMAPPED_TEAM_OPTION in valid_team_names and (
            not dropdown_keywords or include_unmapped_via_keyword
        ):
            team_names.append(UNMAPPED_TEAM_OPTION)
    else:
        team_names = list(valid_team_names)

    return {
        "statuses": statuses,
        "assignees": assignees,
        "teams": sorted(set(team_names), key=str.casefold),
    }


def load_ticket_rows(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
    limit: int | None,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    """Return filtered ticket rows and total count."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    params_with_teams = list(params)
    _append_team_filter_exists(where_parts, params_with_teams, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        count_query = f"SELECT COUNT(*) AS count FROM tickets_current tc {scoped_where_clause}"
        total = int(conn.execute(count_query, params_with_teams).fetchone()["count"])

        query = f"""
            SELECT tc.*
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.updated DESC, tc.ticket_key ASC
        """
        query_params = [*params_with_teams]
        if limit is None:
            if offset > 0:
                query = f"{query}\nLIMIT -1 OFFSET ?"
                query_params.append(offset)
        else:
            query = f"{query}\nLIMIT ? OFFSET ?"
            query_params.extend([limit, offset])

        rows = conn.execute(query, query_params).fetchall()

    member_lookup = _member_to_team_lookup()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = _ticket_from_row(row)
        has_row_team = bool(str(item.get("team_id") or "").strip() or str(item.get("team_name") or "").strip())
        if not has_row_team:
            assignee_key = str(item.get("assignee") or "").strip().casefold()
            team_meta = member_lookup.get(assignee_key)
            if team_meta:
                item["team_id"] = team_meta.get("team_id")
                item["team_name"] = team_meta.get("team_name")
        items.append(item)

    return total, items


def load_ticket_team_groups(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
) -> list[dict[str, Any]]:
    """Return Team -> Member grouped ticket hierarchy with summary badges."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )
    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    params_with_teams = list(params)
    _append_team_filter_exists(where_parts, params_with_teams, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT tc.*
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.assignee COLLATE NOCASE ASC, tc.updated DESC
            """,
            params_with_teams,
        ).fetchall()

    member_lookup = _member_to_team_lookup()
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticket = _ticket_from_row(row)
        assignee = str(ticket.get("assignee") or "").strip() or "Unassigned"
        team_id = str(ticket.get("team_id") or "").strip()
        team_name = str(ticket.get("team_name") or "").strip()

        if not team_id and not team_name:
            team_meta = member_lookup.get(assignee.casefold())
            if team_meta:
                team_id = str(team_meta.get("team_id") or "").strip()
                team_name = str(team_meta.get("team_name") or "").strip()

        if not team_id and not team_name:
            team_id = "unmapped-team"
            team_name = UNMAPPED_TEAM_OPTION

        team_group = grouped.setdefault(
            team_id,
            {
                "team_id": team_id,
                "team_name": team_name,
                "total_tickets": 0,
                "in_progress_tickets": 0,
                "blocked_tickets": 0,
                "members": {},
            },
        )

        team_group["total_tickets"] += 1
        if _status_bucket(ticket.get("status") or "") == "in_progress":
            team_group["in_progress_tickets"] += 1
        dependencies = ticket.get("dependencies") or {}
        blockers = dependencies.get("blockers") if isinstance(dependencies, dict) else []
        if isinstance(blockers, list) and blockers:
            team_group["blocked_tickets"] += 1

        member_group = team_group["members"].setdefault(
            assignee,
            {
                "assignee": assignee,
                "count": 0,
                "items": [],
            },
        )
        member_group["count"] += 1
        member_group["items"].append(ticket)

    groups: list[dict[str, Any]] = []
    for group in grouped.values():
        members = list(group["members"].values())
        members.sort(key=lambda item: (-int(item["count"]), str(item["assignee"]).casefold()))
        groups.append(
            {
                "team_id": group["team_id"],
                "team_name": group["team_name"],
                "total_tickets": group["total_tickets"],
                "in_progress_tickets": group["in_progress_tickets"],
                "blocked_tickets": group["blocked_tickets"],
                "members": members,
            }
        )

    groups.sort(key=lambda item: (str(item["team_name"]).casefold(), str(item["team_id"])))
    return groups


def _filter_teams_by_keywords(teams: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, Any]]:
    normalized_keywords = [
        _normalize_team_text(keyword)
        for keyword in keywords
        if _normalize_team_text(keyword)
    ]
    if not normalized_keywords:
        return teams

    return [
        team
        for team in teams
        if any(
            keyword in _normalize_team_text(team.get("team_name", ""))
            for keyword in normalized_keywords
        )
    ]


def load_team_roster(team_filters: list[str] | None = None) -> list[dict[str, Any]]:
    """Return unfiltered team roster from source, optionally narrowed by explicit team filters."""
    team_filters = team_filters or []
    teams = _load_team_roster_source()

    if team_filters:
        normalized_filters = {_normalize_team_text(value) for value in team_filters if str(value or "").strip()}
        teams = [
            team
            for team in teams
            if _normalize_team_text(team.get("team_id", "")) in normalized_filters
            or _normalize_team_text(team.get("team_name", "")) in normalized_filters
        ]

    teams.sort(key=lambda item: str(item["team_name"]).casefold())
    return teams


def load_team_roster_for_team_details(team_filters: list[str] | None = None) -> list[dict[str, Any]]:
    """Return team roster scoped by dashboard.team_visibility_keywords from .config."""
    teams = load_team_roster(team_filters=team_filters)
    return _filter_teams_by_keywords(teams, get_team_visibility_keywords())


def load_team_roster_for_dropdown() -> list[dict[str, Any]]:
    """Return Team dropdown roster scoped by dashboard.team_dropdown_keywords from .config.

    Empty keyword list means all teams are shown.
    """
    teams = load_team_roster(team_filters=None)
    return _filter_teams_by_keywords(teams, get_team_dropdown_keywords())


def load_team_workspace_overview(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return team cards driven by JSON/CSV source-of-truth roster."""
    roster = load_team_roster_for_team_details(team_filters=teams)

    # To get metric numbers for all teams under current filters, let's load all tickets matching non-team filters
    total, all_tickets = load_ticket_rows(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=[], # do not restrict to teams here so we can see other teams' ticket metrics
        search=search,
        board_id=board_id,
        limit=99999,
        offset=0,
    )

    team_metrics = {}
    for team in roster:
        t_id = team.get("team_id")
        team_metrics[t_id] = {
            "total_assigned": 0,
            "in_progress": 0,
            "blocked": 0,
            "reported": 0,
        }

    for ticket in all_tickets:
        ticket_team_id = ticket.get("team_id")
        if ticket_team_id in team_metrics:
            metrics = team_metrics[ticket_team_id]
            metrics["total_assigned"] += 1
            if _status_bucket(str(ticket.get("status") or "")) == "in_progress":
                metrics["in_progress"] += 1
            dependencies = ticket.get("dependencies") or {}
            blockers = dependencies.get("blockers") if isinstance(dependencies, dict) else []
            if isinstance(blockers, list) and blockers:
                metrics["blocked"] += 1

    # Map database reporters to teams dynamically
    with get_connection() as conn:
        try:
            all_reporters = conn.execute("SELECT DISTINCT reporter FROM tickets_current WHERE reporter IS NOT NULL AND reporter != ''").fetchall()
            reporter_names = [row["reporter"] for row in all_reporters]
        except sqlite3.OperationalError:
            reporter_names = []

    reporter_to_team_id = {}
    for rep in reporter_names:
        matched_csv = match_assignee_to_member(rep)
        if matched_csv:
            for team in roster:
                if any(str(m.get("display_name") or "").strip().casefold() == matched_csv.casefold() for m in team.get("members", [])):
                    reporter_to_team_id[rep.strip().casefold()] = team.get("team_id")

    for ticket in all_tickets:
        reporter_raw = str(ticket.get("reporter") or "").strip().casefold()
        if reporter_raw in reporter_to_team_id:
            rep_team_id = reporter_to_team_id[reporter_raw]
            if rep_team_id in team_metrics:
                team_metrics[rep_team_id]["reported"] += 1

    cards: list[dict[str, Any]] = []
    for team in roster:
        team_id = str(team.get("team_id") or "")
        metrics = team_metrics.get(team_id, {
            "total_assigned": 0,
            "in_progress": 0,
            "blocked": 0,
            "reported": 0,
        })
        cards.append(
            {
                "team_id": team_id,
                "team_name": team.get("team_name", ""),
                "description": team.get("description", ""),
                "member_count": len(team.get("members", [])),
                "members": team.get("members", []),
                "metrics": metrics,
            }
        )

    has_other_filter = bool(statuses or assignees or excluded_statuses or excluded_assignees or search or board_id)
    if has_other_filter:
        cards = [
            card for card in cards
            if card["metrics"]["total_assigned"] > 0 or card["metrics"]["reported"] > 0
        ]

    return {
        "teams": cards,
        "counts": {
            "teams": len(cards),
            "members": sum(int(card.get("member_count") or 0) for card in cards),
        },
    }


def load_team_detail_tabs(
    team_id: str,
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return team detail data sourced from CSV roster."""
    team_roster = load_team_roster_for_team_details(team_filters=[team_id])
    team_meta = team_roster[0] if team_roster else {}

    total_assigned, assigned_items = load_ticket_rows(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=[team_id],
        search=search,
        board_id=board_id,
        limit=99999,
        offset=0,
    )

    cnt_in_progress = 0
    cnt_blocked = 0
    for item in assigned_items:
        if _status_bucket(str(item.get("status") or "")) == "in_progress":
            cnt_in_progress += 1
        dependencies = item.get("dependencies") or {}
        blockers = dependencies.get("blockers") if isinstance(dependencies, dict) else []
        if isinstance(blockers, list) and blockers:
            cnt_blocked += 1

    work_done = [item for item in assigned_items if _status_bucket(str(item.get("status") or "")) == "done"]

    all_team_members = {
        str(member.get("display_name") or "").strip().casefold()
        for member in team_meta.get("members", [])
        if str(member.get("display_name") or "").strip()
    }

    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    with get_connection() as conn:
        try:
            all_reported_rows = conn.execute(
                f"""
                SELECT tc.*
                FROM tickets_current tc
                {where_clause}
                ORDER BY tc.updated DESC, tc.ticket_key ASC
                """,
                params
            ).fetchall()
        except sqlite3.OperationalError:
            all_reported_rows = []

    reported_items = []
    for row in all_reported_rows:
        ticket = _ticket_from_row(row)
        rep = str(ticket.get("reporter") or "").strip()
        matched_csv = match_assignee_to_member(rep)
        if matched_csv and matched_csv.casefold() in all_team_members:
            ticket["team_id"] = team_meta.get("team_id")
            ticket["team_name"] = team_meta.get("team_name")
            reported_items.append(ticket)

    timeline = {
        "todo": 0,
        "in_progress": 0,
        "done": 0,
        "total": len(assigned_items),
    }
    for item in assigned_items:
        bucket = _status_bucket(str(item.get("status") or ""))
        timeline[bucket] += 1

    return {
        "team": {
            "team_id": team_meta.get("team_id") or team_id,
            "team_name": team_meta.get("team_name") or "",
            "description": team_meta.get("description") or "",
            "members": team_meta.get("members", []),
        },
        "tickets_assigned": {
            "metrics": {
                "total": len(assigned_items),
                "in_progress": cnt_in_progress,
                "blocked": cnt_blocked,
            },
            "items": assigned_items,
        },
        "work_done": {
            "count": len(work_done),
            "items": work_done,
        },
        "tickets_reported": {
            "count": len(reported_items),
            "items": reported_items,
        },
        "timeline": timeline,
    }


def load_team_filter_options(
    search: str | None,
    board_id: str | None,
    selected_teams: list[str],
) -> dict[str, list[str]]:
    """Return filter options with team list and cascaded assignee options."""
    return load_filter_options(
        search=search,
        board_id=board_id,
        teams=selected_teams,
    )


def load_grouped_tickets_by_team(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
    limit: int | None,
    offset: int,
) -> dict[str, Any]:
    """Return Team -> Member grouped payload compatible with tickets endpoint."""
    total, rows = load_ticket_rows(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=teams,
        search=search,
        board_id=board_id,
        limit=limit,
        offset=offset,
    )

    groups = load_ticket_team_groups(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=teams,
        search=search,
        board_id=board_id,
    )

    # Preserve paging total while exposing grouped payload.
    return {
        "total": total,
        "items": rows,
        "groups": [
            {
                "team_id": group.get("team_id"),
                "team_name": group.get("team_name"),
                "metrics": {
                    "total": group.get("total_tickets", 0),
                    "in_progress": group.get("in_progress_tickets", 0),
                    "blocked": group.get("blocked_tickets", 0),
                },
                "members": [
                    {
                        "member_name": member.get("assignee", ""),
                        "count": member.get("count", 0),
                        "items": member.get("items", []),
                    }
                    for member in group.get("members", [])
                ],
            }
            for group in groups
        ],
    }


def load_teams_workspace_data(
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    teams: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return data payload for teams workspace."""
    return load_team_workspace_overview(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        teams=teams,
        search=search,
        board_id=board_id,
    )


def load_team_detail_panels(
    team_id: str,
    statuses: list[str],
    assignees: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return team detail panel payload for the frontend tabs."""
    return load_team_detail_tabs(
        team_id=team_id,
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
    )


def calculate_metrics(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return dashboard KPI and dependency metrics for filtered ticket scope."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    scoped_params = list(params)
    _append_team_filter_exists(where_parts, scoped_params, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        by_status_rows = conn.execute(
            f"""
            SELECT tc.status, COUNT(*) AS count
            FROM tickets_current tc
            {scoped_where_clause}
            GROUP BY tc.status
            ORDER BY tc.status ASC
            """,
            scoped_params,
        ).fetchall()

        active_tickets = sum(
            int(row["count"])
            for row in by_status_rows
            if _is_active_ticket_status(row["status"])
        )

        open_bug_count = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM tickets_current tc
                {_extend_where_clause(scoped_where_clause, "LOWER(tc.issue_type) = 'bug' AND (tc.resolution_date IS NULL OR tc.resolution_date = '')")}
                """,
                scoped_params,
            ).fetchone()["count"]
        )

        stale_tickets = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM tickets_current tc
                {_extend_where_clause(scoped_where_clause, "(tc.updated IS NULL OR tc.updated = '' OR datetime(tc.updated) <= datetime('now', '-14 day'))")}
                """,
                scoped_params,
            ).fetchone()["count"]
        )

        dependency_where_clause = scoped_where_clause.replace("WHERE", "", 1).strip()
        if dependency_where_clause:
            dependency_where = (
                "WHERE source_ticket_key IN (SELECT tc.ticket_key FROM tickets_current tc "
                f"{scoped_where_clause})"
            )
            dependency_params = scoped_params
        else:
            dependency_where = ""
            dependency_params = []

        blockers = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ticket_dependencies_current
                {dependency_where}
                {'AND' if dependency_where else 'WHERE'} dependency_type = 'blockers'
                """,
                dependency_params,
            ).fetchone()["count"]
        )

        inter_team = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ticket_dependencies_current
                {dependency_where}
                {'AND' if dependency_where else 'WHERE'} classification = 'inter_team'
                """,
                dependency_params,
            ).fetchone()["count"]
        )

        intra_team = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ticket_dependencies_current
                {dependency_where}
                {'AND' if dependency_where else 'WHERE'} classification = 'intra_team'
                """,
                dependency_params,
            ).fetchone()["count"]
        )

    return {
        "kpis": {
            "total_active_tickets": active_tickets,
            "open_bug_count": open_bug_count,
            "stale_tickets_over_14_days": stale_tickets,
        },
        "active_by_status": [
            {"status": row["status"] or "Unknown", "count": int(row["count"])} for row in by_status_rows
        ],
        "dependency_summary": {
            "blockers": blockers,
            "inter_team": inter_team,
            "intra_team": intra_team,
        },
    }


def _is_active_ticket_status(status: str | None) -> bool:
    """Return True when a ticket status should count as active in the overview KPI."""
    normalized = " ".join(str(status or "").strip().lower().split())
    if not normalized:
        return True

    if normalized in {"done", "rejected"}:
        return False

    # Exclude explicit and prefixed todo-style statuses (for example: "to do", "sqa to do").
    compact = normalized.replace(" ", "")
    if compact == "todo" or compact.endswith("todo"):
        return False

    return True


def build_network_graph(
    statuses: list[str],
    assignees: list[str],
    teams: list[str],
    excluded_statuses: list[str],
    excluded_assignees: list[str],
    search: str | None,
    board_id: str | None,
) -> dict[str, Any]:
    """Return network graph nodes/edges from filtered ticket scope and dependencies."""
    where_clause, params = _build_ticket_filter_clause(
        statuses=statuses,
        assignees=assignees,
        excluded_statuses=excluded_statuses,
        excluded_assignees=excluded_assignees,
        search=search,
        board_id=board_id,
        table_alias="tc",
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause.replace("WHERE", "", 1).strip())
    scoped_params = list(params)
    _append_team_filter_exists(where_parts, scoped_params, "tc.assignee", teams)
    scoped_where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    with get_connection() as conn:
        ticket_rows = conn.execute(
            f"""
            SELECT tc.ticket_key, tc.summary, tc.status, tc.assignee, tc.priority, tc.reporter, tc.issue_type, tc.story_points
            FROM tickets_current tc
            {scoped_where_clause}
            ORDER BY tc.ticket_key ASC
            """,
            scoped_params,
        ).fetchall()

        edge_where_clause = (
            "WHERE source_ticket_key IN (SELECT tc.ticket_key FROM tickets_current tc "
            f"{scoped_where_clause})"
            if scoped_where_clause
            else ""
        )
        edge_params = [*scoped_params] if scoped_where_clause else []

        dep_rows = conn.execute(
            f"""
            SELECT source_ticket_key, target_ticket_key, relation_name, relation_description,
                   dependency_type, classification, target_status
            FROM ticket_dependencies_current
            {edge_where_clause}
            ORDER BY source_ticket_key ASC, target_ticket_key ASC
            """,
            edge_params,
        ).fetchall()

        node_map: dict[str, dict[str, Any]] = {
            str(row["ticket_key"]): {
                "id": row["ticket_key"],
                "ticket_key": row["ticket_key"],
                "summary": row["summary"],
                "status": row["status"],
                "assignee": row["assignee"],
                "priority": row["priority"],
                "reporter": row["reporter"],
                "issue_type": row["issue_type"],
                "story_points": row["story_points"],
            }
            for row in ticket_rows
        }

        target_status_by_key: dict[str, str] = {}
        missing_target_keys: set[str] = set()
        for row in dep_rows:
            target_key = str(row["target_ticket_key"] or "").strip()
            if not target_key:
                continue
            if target_key not in node_map:
                missing_target_keys.add(target_key)
            target_status_by_key[target_key] = str(row["target_status"] or "").strip()

        if missing_target_keys:
            placeholders = ", ".join("?" for _ in missing_target_keys)
            external_rows = conn.execute(
                f"""
                SELECT ticket_key, summary, status, assignee, priority, reporter, issue_type, story_points
                FROM tickets_current
                WHERE ticket_key IN ({placeholders})
                """,
                list(missing_target_keys),
            ).fetchall()

            for row in external_rows:
                node_map[str(row["ticket_key"])] = {
                    "id": row["ticket_key"],
                    "ticket_key": row["ticket_key"],
                    "summary": row["summary"],
                    "status": row["status"],
                    "assignee": row["assignee"],
                    "priority": row["priority"],
                    "reporter": row["reporter"],
                    "issue_type": row["issue_type"],
                    "story_points": row["story_points"],
                }

        for target_key in missing_target_keys:
            if target_key in node_map:
                continue
            node_map[target_key] = {
                "id": target_key,
                "ticket_key": target_key,
                "summary": "Dependency target outside cached ticket scope",
                "status": target_status_by_key.get(target_key, "Unknown"),
                "assignee": "",
                "priority": "",
                "reporter": "",
                "issue_type": "",
                "story_points": None,
            }

    connected_keys: set[str] = set()
    edges: list[dict[str, Any]] = []
    for row in dep_rows:
        source_key = str(row["source_ticket_key"] or "").strip()
        target_key = str(row["target_ticket_key"] or "").strip()
        if not source_key or not target_key:
            continue
        connected_keys.add(source_key)
        connected_keys.add(target_key)
        edges.append(
            {
                "source_ticket": source_key,
                "target_ticket": target_key,
                "relation_name": row["relation_name"],
                "relation_description": row["relation_description"],
                "dependency_type": row["dependency_type"],
                "classification": row["classification"],
            }
        )

    nodes = sorted(
        [node for key, node in node_map.items() if key in connected_keys],
        key=lambda node: str(node.get("ticket_key") or ""),
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
        },
    }
