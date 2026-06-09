from __future__ import annotations

import csv
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

        # Create a mock CSV for team details
        self.mock_csv_path = Path(self.temp_dir) / "team_details_test.csv"
        with open(self.mock_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Infrastructure Team", "", "", "", "", ""])
            writer.writerow(["Name", "Role", "Skillset", "Location", "Contractor", "Notes"])
            writer.writerow(["Jeremy Pierson", "Senior Eng", "", "Boulder", "No", ""])
            writer.writerow(["Minh Dang", "", "", "", "", ""])
            writer.writerow(["", "", "", "", "", ""]) # separator empty row
            writer.writerow(["Reflect Analytics", "", "", "", "", ""])
            writer.writerow(["Name", "Role", "Skillset", "Location", "Contractor", "Notes"])
            writer.writerow(["Abinash", "QA", "", "", "Yes", ""])

        self._csv_path_patcher = patch("database.TEAM_DETAILS_CSV_PATH", self.mock_csv_path)
        self._csv_path_patcher.start()

    def tearDown(self) -> None:
        self._csv_path_patcher.stop()
        self._db_path_patcher.stop()
        self._temp_dir_ctx.cleanup()

    def _insert_ticket(self, key: str, summary: str, assignee: str, status: str = "In Progress") -> None:
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tickets_current (
                    ticket_key, project_key, summary, issue_type, status, priority,
                    assignee, reporter, report_date, due_date, resolution_date, updated,
                    story_points, time_original_estimate, time_estimate, time_spent,
                    source_links_json, dependencies_json, last_seen_run_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                )
            )
            conn.commit()

    def test_roster_parsing_separates_teams_and_members_correctly(self) -> None:
        roster = database._load_team_roster_from_csv()
        self.assertEqual(len(roster), 2)

        # Team 1: Infrastructure Team
        self.assertEqual(roster[0]["team_name"], "Infrastructure Team")
        self.assertEqual(roster[0]["team_id"], "infrastructure-team")
        members_1 = roster[0]["members"]
        self.assertEqual(len(members_1), 2)
        self.assertEqual(members_1[0]["display_name"], "Jeremy Pierson")
        self.assertEqual(members_1[0]["role"], "Senior Eng")
        self.assertEqual(members_1[1]["display_name"], "Minh Dang")

        # Team 2: Reflect Analytics
        self.assertEqual(roster[1]["team_name"], "Reflect Analytics")
        self.assertEqual(roster[1]["team_id"], "reflect-analytics")
        members_2 = roster[1]["members"]
        self.assertEqual(len(members_2), 1)
        self.assertEqual(members_2[0]["display_name"], "Abinash")
        self.assertEqual(members_2[0]["role"], "QA")

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


if __name__ == "__main__":
    unittest.main()
