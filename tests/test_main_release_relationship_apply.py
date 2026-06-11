from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main


class MainReleaseRelationshipApplyTests(unittest.TestCase):
    @patch("main.get_release_relationship_maps")
    @patch("main.reconcile_release_relationships")
    @patch("main.save_release_relationship_updates")
    @patch("main.fetch_release_details")
    def test_apply_passes_depended_by_ids_and_returns_payload(
        self,
        fetch_release_details,
        save_release_relationship_updates,
        reconcile_release_relationships,
        get_release_relationship_maps,
    ) -> None:
        fetch_release_details.return_value = {
            "releases": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        }
        save_release_relationship_updates.return_value = {
            "selected_count": 1,
            "dependencies_deleted": 0,
            "coreleases_deleted": 0,
            "dependencies_inserted": 2,
            "coreleases_inserted": 0,
        }
        reconcile_release_relationships.return_value = {
            "dependencies_removed": 0,
            "coreleases_removed": 0,
        }
        get_release_relationship_maps.return_value = {
            "dependencies": {"A": [], "B": ["A"], "C": ["A"]},
            "co_releases": {"A": [], "B": [], "C": []},
        }

        payload = main.apply_release_relationships(
            body=main.ReleaseRelationshipApplyRequest(
                selected_release_ids=["A"],
                depends_on_ids=[],
                depended_by_ids=["B", "C"],
                co_release_ids=[],
                active_release_ids=["A", "B", "C"],
            )
        )

        self.assertIn("updated", payload)
        self.assertIn("relationships", payload)

        _, kwargs = save_release_relationship_updates.call_args
        self.assertEqual(kwargs["selected_release_ids"], ["A"])
        self.assertEqual(kwargs["depended_by_ids"], ["B", "C"])

    @patch("main.get_release_relationship_maps")
    @patch("main.reconcile_release_relationships")
    @patch("main.save_release_relationship_updates")
    @patch("main.fetch_release_details")
    def test_apply_excludes_archived_releases_from_live_active_ids(
        self,
        fetch_release_details,
        save_release_relationship_updates,
        reconcile_release_relationships,
        get_release_relationship_maps,
    ) -> None:
        fetch_release_details.return_value = {
            "releases": [
                {"id": "A", "archived": False},
                {"id": "B", "status": "Archived"},
                {"id": "C", "released": False},
            ],
        }
        save_release_relationship_updates.return_value = {}
        reconcile_release_relationships.return_value = {}
        get_release_relationship_maps.return_value = {
            "dependencies": {},
            "co_releases": {},
        }

        main.apply_release_relationships(
            body=main.ReleaseRelationshipApplyRequest(
                selected_release_ids=["A"],
                depends_on_ids=[],
                depended_by_ids=["C"],
                co_release_ids=[],
                active_release_ids=[],
            )
        )

        _, kwargs = save_release_relationship_updates.call_args
        self.assertEqual(kwargs["active_release_ids"], ["A", "C"])

    @patch("main.fetch_release_details")
    def test_apply_returns_502_when_release_source_fails(self, fetch_release_details) -> None:
        fetch_release_details.return_value = {
            "releases": [],
            "error": "source unavailable",
        }

        with self.assertRaises(HTTPException) as raised:
            main.apply_release_relationships(
                body=main.ReleaseRelationshipApplyRequest(
                    selected_release_ids=["A"],
                    depends_on_ids=[],
                    depended_by_ids=[],
                    co_release_ids=[],
                    active_release_ids=["A"],
                )
            )

        self.assertEqual(raised.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
