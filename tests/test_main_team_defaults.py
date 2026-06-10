from __future__ import annotations

import unittest
from unittest.mock import patch

import main


class MainTeamDefaultsTests(unittest.TestCase):
    def test_resolve_effective_team_values_uses_selected_when_present(self) -> None:
        selected = ["Reflect Analytics", "DevOps"]
        with patch("main._load_team_filter_options") as mocked:
            result = main._resolve_effective_team_values(
                selected_teams=selected,
                search=None,
                board_id=None,
            )

        self.assertEqual(result, selected)
        mocked.assert_not_called()

    def test_resolve_effective_team_values_defaults_to_dropdown_options(self) -> None:
        with patch(
            "main._load_team_filter_options",
            return_value={"teams": ["Reflect Analytics", "Unmapped Team"]},
        ) as mocked:
            result = main._resolve_effective_team_values(
                selected_teams=[],
                search=None,
                board_id=None,
            )

        self.assertEqual(result, ["Reflect Analytics", "Unmapped Team"])
        mocked.assert_called_once()

    def test_get_teams_workspace_does_not_apply_dropdown_defaults(self) -> None:
        with patch("main._resolve_effective_team_values") as mocked_resolve, patch(
            "main.load_teams_workspace_data",
            return_value={"teams": []},
        ) as mocked_workspace:
            payload = main.get_teams_workspace(
                status=None,
                assignee=None,
                team=None,
                status_exclude=None,
                assignee_exclude=None,
                search=None,
                board_id=None,
            )

        self.assertEqual(payload, {"teams": []})
        mocked_resolve.assert_not_called()
        mocked_workspace.assert_called_once_with(
            statuses=[],
            assignees=[],
            teams=[],
            excluded_statuses=[],
            excluded_assignees=[],
            search=None,
            board_id=None,
        )

    def test_get_releases_uses_existing_services_fetch_release_details(self) -> None:
        expected = {
            "fetched_at": "2026-06-10T00:00:00+00:00",
            "project_key": "QSYSCLOUD",
            "releases": [{"name": "Reflect Edge 1.3", "releaseDate": "2026-08-31", "released": False}],
        }
        with patch("main.fetch_release_details", return_value=expected) as mocked_fetch:
            payload = main.get_releases(project_key="QSYSCLOUD")

        self.assertEqual(payload, expected)
        mocked_fetch.assert_called_once_with(project_key="QSYSCLOUD")


if __name__ == "__main__":
    unittest.main()
