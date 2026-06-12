from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main


class MainReleaseRemarksTests(unittest.TestCase):
    @patch("main.load_release_remarks_map")
    @patch("main.fetch_release_details")
    def test_get_releases_hydrates_remarks(self, fetch_release_details, load_release_remarks_map) -> None:
        fetch_release_details.return_value = {
            "project_key": "QSYSCLOUD",
            "releases": [
                {"id": "A", "name": "Alpha", "released": False, "archived": False},
                {"id": "B", "name": "Beta", "released": False, "archived": False},
            ],
        }
        load_release_remarks_map.return_value = {
            "A": "Needs dependency alignment",
            "B": "",
        }

        payload = main.get_releases(project_key="QSYSCLOUD")

        releases = payload.get("releases", [])
        self.assertEqual(len(releases), 2)
        by_id = {str(item.get("id")): item for item in releases}
        self.assertEqual(by_id["A"].get("remarks"), "Needs dependency alignment")
        self.assertEqual(by_id["B"].get("remarks"), "")

    @patch("main.save_release_remark")
    def test_update_release_remarks_returns_payload(self, save_release_remark) -> None:
        save_release_remark.return_value = True

        payload = main.update_release_remarks(
            body=main.ReleaseRemarkUpdateRequest(
                release_id="A",
                remarks="Ready for dry run",
            )
        )

        self.assertEqual(payload["release_id"], "A")
        self.assertEqual(payload["remarks"], "Ready for dry run")

    @patch("main.save_release_remark")
    def test_update_release_remarks_rejects_empty_id(self, save_release_remark) -> None:
        save_release_remark.return_value = True

        with self.assertRaises(HTTPException) as raised:
            main.update_release_remarks(
                body=main.ReleaseRemarkUpdateRequest(
                    release_id="",
                    remarks="ignored",
                )
            )

        self.assertEqual(raised.exception.status_code, 400)

    @patch("main.save_release_remark")
    def test_update_release_remarks_upserts_when_missing(self, save_release_remark) -> None:
        save_release_remark.return_value = True

        payload = main.update_release_remarks(
            body=main.ReleaseRemarkUpdateRequest(
                release_id="missing",
                remarks="x",
            )
        )

        self.assertEqual(payload["release_id"], "missing")
        self.assertEqual(payload["remarks"], "x")


if __name__ == "__main__":
    unittest.main()
