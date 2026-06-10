from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class TicketTeamMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir_ctx = tempfile.TemporaryDirectory()
        self.temp_dir = self._temp_dir_ctx.name
        self.db_path = os.path.join(self.temp_dir, "dashboard_test.db")
        self._db_path_patcher = patch("database.get_database_path", return_value=self.db_path)
        self._db_path_patcher.start()
        database.init_db()

        # Create a mock JSON for team details
        self.mock_json_path = Path(self.temp_dir) / "team_details_test.json"
        mock_data = {
            "members": [
                {
                    "id": 1,
                    "name": "Jeremy Pierson",
                    "location": "Boulder",
                    "skillset": "SQA",
                    "contractor": None,
                    "notes": None,
                    "teams": [
                        {
                            "pod": "Functional Teams",
                            "team": "Infrastructure Team",
                            "role": "Senior Eng"
                        }
                    ]
                },
                {
                    "id": 2,
                    "name": "Minh Dang",
                    "location": "Boulder",
                    "skillset": None,
                    "contractor": None,
                    "notes": None,
                    "teams": [
                        {
                            "pod": "Functional Teams",
                            "team": "Infrastructure Team",
                            "role": None
                        }
                    ]
                },
                {
                    "id": 3,
                    "name": "Abinash",
                    "location": "Bangalore",
                    "skillset": None,
                    "contractor": None,
                    "notes": None,
                    "teams": [
                        {
                            "pod": "Enterprise Manager Pod",
                            "team": "Reflect Analytics",
                            "role": "QA"
                        }
                    ]
                },
                {
                    "id": 4,
                    "name": "Vivek Tiwari",
                    "location": "Bangalore",
                    "skillset": None,
                    "contractor": None,
                    "notes": None,
                    "teams": [
                        {
                            "pod": "Enterprise Manager Pod",
                            "team": "Reflect Subdirectory",
                            "role": "SM"
                        }
                    ]
                }
            ],
            "components": [
                {
                    "project": "QSYSCLOUD",
                    "name": "Infra Platform",
                    "team": "Infrastructure Team",
                },
                {
                    "project": "QSYSCLOUD",
                    "name": "Reflect Analytics Component",
                    "team": "Reflect Analytics",
                },
            ],
        }
        with open(self.mock_json_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        self._json_path_patcher = patch("database.TEAM_DETAILS_JSON_PATH", self.mock_json_path)
        self._json_path_patcher.start()

    def tearDown(self) -> None:
        self._json_path_patcher.stop()
        self._db_path_patcher.stop()
        self._temp_dir_ctx.cleanup()

    def _insert_ticket(self, key: str, summary: str, assignee: str, status: str = "In Progress") -> None:
        # Get team for assignee
        team_id, team_name = database._get_primary_team_for_assignee(assignee)
        
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    "PROJ",
                    summary,
                    "Task",
                    status,
                    "Medium",
                    assignee,
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    team_id,
                    team_name,
                )
            )
            conn.commit()

    def test_roster_parsing_separates_teams_and_members_correctly(self) -> None:
        roster = database._load_team_roster_source()
        
        # Verify that roster has teams
        self.assertGreater(len(roster), 0)
        
        # Verify that Infrastructure Team exists in the roster
        infra_team = next((t for t in roster if t.get("team_name") == "Infrastructure Team"), None)
        self.assertIsNotNone(infra_team)
        self.assertEqual(infra_team["team_id"], "infrastructure-team")
        self.assertGreater(len(infra_team["members"]), 0)
        
        # Verify that Reflect Analytics exists in the roster
        analytics_team = next((t for t in roster if t.get("team_name") == "Reflect Analytics"), None)
        self.assertIsNotNone(analytics_team)
        self.assertEqual(analytics_team["team_id"], "reflect-analytics")
        self.assertGreater(len(analytics_team["members"]), 0)

    def test_team_filter_by_team_id_and_team_name(self) -> None:
        self._insert_ticket("ABC-1", "Infra ticket", "Jeremy Pierson")
        self._insert_ticket("ABC-2", "Analytics ticket", "Abinash")

        # Filter by team name
        total, rows = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["Infrastructure Team"],
            search=None,
            board_id=None,
            limit=100,
            offset=0,
        )
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_key"], "ABC-1")
        self.assertEqual(rows[0]["team_id"], "infrastructure-team")

        # Case insensitive filter by team id
        total, rows = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["reflect-analytics"],
            search=None,
            board_id=None,
            limit=100,
            offset=0,
        )
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_key"], "ABC-2")
        self.assertEqual(rows[0]["team_id"], "reflect-analytics")

    def test_load_ticket_team_groups(self) -> None:
        self._insert_ticket("ABC-1", "Infra ticket", "Jeremy Pierson")
        self._insert_ticket("ABC-2", "Analytics ticket", "Abinash")

        groups = database.load_ticket_team_groups(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=[],
            search=None,
            board_id=None,
        )

        # Result is sorted by team name case-insensitively
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["team_id"], "infrastructure-team")
        self.assertEqual(groups[0]["total_tickets"], 1)
        self.assertEqual(groups[1]["team_id"], "reflect-analytics")
        self.assertEqual(groups[1]["total_tickets"], 1)

    def test_team_filter_supports_legacy_rows_without_team_columns(self) -> None:
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "LEGACY-1",
                    "PROJ",
                    "Legacy infra ticket",
                    "Task",
                    "In Progress",
                    "Medium",
                    "Jeremy Pierson",
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    "",
                    "",
                ),
            )
            conn.commit()

        total, rows = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["Infrastructure Team"],
            search=None,
            board_id=None,
            limit=100,
            offset=0,
        )

        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_key"], "LEGACY-1")

    def test_team_filter_is_case_and_whitespace_tolerant(self) -> None:
        self._insert_ticket("ABC-3", "Infra ticket 2", "Jeremy Pierson")

        total, rows = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["  INFRASTRUCTURE TEAM  "],
            search=None,
            board_id=None,
            limit=100,
            offset=0,
        )

        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_key"], "ABC-3")

    def test_filter_options_include_teams_from_stored_tickets(self) -> None:
        self._insert_ticket("ABC-4", "Infra ticket 3", "Jeremy Pierson")
        options = database.load_filter_options(
            search=None,
            board_id=None,
            teams=["Infrastructure Team"],
        )

        self.assertIn("Infrastructure Team", options.get("teams", []))
        self.assertNotIn("Reflect Analytics", options.get("teams", []))

    def test_team_visibility_keywords_filter_is_case_insensitive(self) -> None:
        with patch("database.get_team_visibility_keywords", return_value=["INFRA", "reflect"]):
            roster = database.load_team_roster_for_team_details()

        team_names = {str(team.get("team_name") or "") for team in roster}
        self.assertIn("Infrastructure Team", team_names)
        self.assertIn("Reflect Analytics", team_names)

    def test_team_visibility_keywords_filter_excludes_non_matching_teams(self) -> None:
        with patch("database.get_team_visibility_keywords", return_value=["infra"]):
            roster = database.load_team_roster_for_team_details()

        team_names = [str(team.get("team_name") or "") for team in roster]
        self.assertIn("Infrastructure Team", team_names)
        self.assertNotIn("Reflect Analytics", team_names)

    def test_team_dropdown_keywords_filter_is_independent_of_visibility_filter(self) -> None:
        self._insert_ticket("ABC-9", "Infra ticket 6", "Jeremy Pierson")
        self._insert_ticket("ABC-10", "Analytics ticket 4", "Abinash")
        with patch("database.get_team_visibility_keywords", return_value=["reflect"]), patch(
            "database.get_team_dropdown_keywords", return_value=[]
        ):
            options = database.load_filter_options(search=None, board_id=None, teams=[])

        self.assertIn("Infrastructure Team", options.get("teams", []))
        self.assertIn("Reflect Analytics", options.get("teams", []))

    def test_team_dropdown_keywords_filter_can_restrict_dropdown_options(self) -> None:
        self._insert_ticket("ABC-5", "Infra ticket 4", "Jeremy Pierson")
        self._insert_ticket("ABC-6", "Analytics ticket 2", "Abinash")
        with patch("database.get_team_dropdown_keywords", return_value=["infra"]):
            options = database.load_filter_options(search=None, board_id=None, teams=[])

        self.assertIn("Infrastructure Team", options.get("teams", []))
        self.assertNotIn("Reflect Analytics", options.get("teams", []))

    def test_team_dropdown_keywords_can_include_unmapped_option(self) -> None:
        self._insert_ticket("ABC-13", "Infra ticket 9", "Jeremy Pierson")
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "LEGACY-UNMAPPED-3",
                    "PROJ",
                    "Unmapped ticket 3",
                    "Task",
                    "In Progress",
                    "Medium",
                    "Unknown Person",
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    "",
                    "",
                ),
            )
            conn.commit()

        with patch("database.get_team_dropdown_keywords", return_value=["infra", "unmapped"]):
            options = database.load_filter_options(search=None, board_id=None, teams=[])

        self.assertIn("Infrastructure Team", options.get("teams", []))
        self.assertIn("Unmapped Team", options.get("teams", []))

    def test_team_dropdown_options_ignore_active_team_filter(self) -> None:
        self._insert_ticket("ABC-7", "Infra ticket 5", "Jeremy Pierson")
        self._insert_ticket("ABC-8", "Analytics ticket 3", "Abinash")

        options = database.load_filter_options(
            search=None,
            board_id=None,
            teams=["Infrastructure Team"],
        )

        self.assertIn("Infrastructure Team", options.get("teams", []))
        self.assertIn("Reflect Analytics", options.get("teams", []))

    def test_selecting_all_team_options_includes_unmapped_tickets(self) -> None:
        self._insert_ticket("ABC-11", "Infra ticket 7", "Jeremy Pierson")
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "LEGACY-UNMAPPED-1",
                    "PROJ",
                    "Unmapped ticket",
                    "Task",
                    "In Progress",
                    "Medium",
                    "Unknown Person",
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    "",
                    "",
                ),
            )
            conn.commit()

        total_all, _ = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=[],
            search=None,
            board_id=None,
            limit=999,
            offset=0,
        )

        with patch("database.get_team_dropdown_keywords", return_value=[]):
            options = database.load_filter_options(search=None, board_id=None, teams=[])
        self.assertIn("Unmapped Team", options.get("teams", []))

        total_selected, _ = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=options.get("teams", []),
            search=None,
            board_id=None,
            limit=999,
            offset=0,
        )

        self.assertEqual(total_selected, total_all)

    def test_selecting_only_unmapped_team_excludes_mapped_tickets(self) -> None:
        self._insert_ticket("ABC-12", "Infra ticket 8", "Jeremy Pierson")
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "LEGACY-UNMAPPED-2",
                    "PROJ",
                    "Another unmapped ticket",
                    "Task",
                    "In Progress",
                    "Medium",
                    "Unknown Person",
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    "",
                    "",
                ),
            )
            conn.commit()

        total_unmapped, rows_unmapped = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["Unmapped Team"],
            search=None,
            board_id=None,
            limit=999,
            offset=0,
        )

        self.assertEqual(total_unmapped, 1)
        self.assertEqual(len(rows_unmapped), 1)
        self.assertEqual(rows_unmapped[0]["ticket_key"], "LEGACY-UNMAPPED-2")

    def test_resolve_ticket_team_prefers_components_over_assignee(self) -> None:
        ticket = {
            "assignee": "Jeremy Pierson",  # Infrastructure Team by assignee mapping
            "components": [{"name": "Reflect Analytics"}],
        }
        team_id, team_name = database._resolve_ticket_team(ticket)
        self.assertEqual(team_id, "reflect-analytics")
        self.assertEqual(team_name, "Reflect Analytics")

    def test_resolve_ticket_teams_supports_multiple_components(self) -> None:
        ticket = {
            "assignee": "Jeremy Pierson",
            "components": [
                {"name": "Infrastructure Team"},
                {"name": "Reflect Analytics"},
            ],
        }
        teams = database._resolve_ticket_teams(ticket)
        team_ids = {team_id for team_id, _team_name in teams}
        self.assertIn("infrastructure-team", team_ids)
        self.assertIn("reflect-analytics", team_ids)

    def test_resolve_ticket_teams_uses_component_alias_mapping(self) -> None:
        ticket = {
            "assignee": "Unknown",
            "components": [{"name": "Infra Platform"}],
        }
        teams = database._resolve_ticket_teams(ticket)
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0][0], "infrastructure-team")
        self.assertEqual(teams[0][1], "Infrastructure Team")

    def test_resolve_ticket_teams_uses_default_reflect_directory_alias(self) -> None:
        ticket = {
            "assignee": "Unknown",
            "components": [{"name": "Reflect Directory"}],
        }
        teams = database._resolve_ticket_teams(ticket)
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0][0], "reflect-subdirectory")
        self.assertEqual(teams[0][1], "Reflect Subdirectory")

    def test_resolve_ticket_teams_uses_default_cloud_services_alias(self) -> None:
        ticket = {
            "assignee": "Unknown",
            "components": [{"name": "Cloud Services"}],
        }
        teams = database._resolve_ticket_teams(ticket)
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0][0], "infrastructure-team")
        self.assertEqual(teams[0][1], "Infrastructure Team")

    def test_find_misclassified_unmapped_tickets_flags_component_mappable_rows(self) -> None:
        tickets = [
            {
                "ticket_key": "QSYS-1",
                "team_name": "Unmapped Team",
                "components": [{"name": "Reflect Analytics"}],
            },
            {
                "ticket_key": "QSYS-2",
                "team_name": "",
                "components": [{"name": "Unknown Component"}],
            },
            {
                "ticket_key": "QSYS-3",
                "team_name": "Infrastructure Team",
                "components": [{"name": "Infrastructure Team"}],
            },
        ]

        misclassified = database.find_misclassified_unmapped_tickets(tickets)
        self.assertEqual(len(misclassified), 1)
        self.assertEqual(misclassified[0]["ticket_key"], "QSYS-1")
        resolved_ids = {row["team_id"] for row in misclassified[0]["resolved_teams"]}
        self.assertIn("reflect-analytics", resolved_ids)

    def test_load_ticket_rows_preserves_stored_team_assignment(self) -> None:
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "COMP-1",
                    "PROJ",
                    "Component mapped ticket",
                    "Task",
                    "In Progress",
                    "Medium",
                    "Jeremy Pierson",
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    "reflect-analytics",
                    "Reflect Analytics",
                ),
            )
            conn.commit()

        total, rows = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["Reflect Analytics"],
            search=None,
            board_id=None,
            limit=100,
            offset=0,
        )
        self.assertEqual(total, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ticket_key"], "COMP-1")
        self.assertEqual(rows[0]["team_id"], "reflect-analytics")

    def test_load_ticket_rows_supports_multi_team_json_membership_filter(self) -> None:
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at,
                    team_id, team_name, team_ids_json, team_names_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "MULTI-1",
                    "PROJ",
                    "Multi-team component mapped ticket",
                    "Task",
                    "In Progress",
                    "Medium",
                    "Unknown Person",
                    "Reporter",
                    "2026-06-01T00:00:00Z",
                    None,
                    None,
                    "2026-06-09T00:00:00Z",
                    3.0,
                    3600,
                    2400,
                    1200,
                    "[]",
                    "{}",
                    "run-id",
                    "2026-06-09T00:00:00Z",
                    "infrastructure-team",
                    "Infrastructure Team",
                    json.dumps(["infrastructure-team", "reflect-analytics"]),
                    json.dumps(["Infrastructure Team", "Reflect Analytics"]),
                ),
            )
            conn.commit()

        total, rows = database.load_ticket_rows(
            statuses=[],
            assignees=[],
            excluded_statuses=[],
            excluded_assignees=[],
            teams=["Reflect Analytics"],
            search=None,
            board_id=None,
            limit=100,
            offset=0,
        )
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["ticket_key"], "MULTI-1")

    def test_persist_extraction_result_stores_multi_team_json(self) -> None:
        payload = {
            "results": [
                {
                    "ticket_key": "PERSIST-1",
                    "summary": "Persist multi-team",
                    "issue_type": "Task",
                    "status": "In Progress",
                    "priority": "Medium",
                    "assignee": "Unknown Person",
                    "reporter": "Reporter",
                    "report_date": "2026-06-01T00:00:00Z",
                    "due_date": None,
                    "resolution_date": None,
                    "updated": "2026-06-09T00:00:00Z",
                    "story_points": 3,
                    "time_original_estimate": 3600,
                    "time_estimate": 2400,
                    "time_spent": 1200,
                    "source_links": [],
                    "dependencies": {},
                    "components": [
                        {"name": "Infrastructure Team"},
                        {"name": "Reflect Analytics"},
                    ],
                }
            ],
            "counts": {},
            "errors": [],
            "partial_errors": [],
            "unresolved_links": [],
        }

        database.persist_extraction_result(payload, trigger_type="manual")
        with database.get_connection() as conn:
            row = conn.execute(
                """
                SELECT team_id, team_name, team_ids_json, team_names_json
                FROM tickets_current WHERE ticket_key = ?
                """,
                ("PERSIST-1",),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["team_id"], "infrastructure-team")
        self.assertEqual(row["team_name"], "Infrastructure Team")
        self.assertIn("reflect-analytics", json.loads(row["team_ids_json"] or "[]"))
        self.assertIn("Reflect Analytics", json.loads(row["team_names_json"] or "[]"))


if __name__ == "__main__":
    unittest.main()
