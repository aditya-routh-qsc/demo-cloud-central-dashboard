from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from database import load_release_remarks_map, save_release_remark


class ReleaseRemarksDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="release_remarks_", suffix=".db")
        os.close(fd)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS release_remarks (
                    release_id TEXT PRIMARY KEY,
                    remarks TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO release_remarks(release_id, remarks, updated_at) VALUES (?, ?, datetime('now'))",
                ("A", "initial note"),
            )
            conn.commit()

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_save_release_remark_updates_row(self) -> None:
        updated = save_release_remark("A", "updated note", db_path=self.db_path)
        self.assertTrue(updated)

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT remarks FROM release_remarks WHERE release_id = ?",
                ("A",),
            ).fetchone()
        self.assertEqual(row[0], "updated note")

    def test_load_release_remarks_map_returns_requested_ids(self) -> None:
        remarks = load_release_remarks_map(["A", "MISSING"], db_path=self.db_path)
        self.assertEqual(remarks.get("A"), "initial note")
        self.assertNotIn("MISSING", remarks)


if __name__ == "__main__":
    unittest.main()
