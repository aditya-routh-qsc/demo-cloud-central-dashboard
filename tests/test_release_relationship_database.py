from __future__ import annotations

from pathlib import Path
import os
import sqlite3
import tempfile
import unittest

from database import (
    get_release_relationship_maps,
    init_release_relationship_schema,
    reconcile_release_relationships,
    save_release_relationship_updates,
)


class ReleaseRelationshipDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(prefix="release_rel_", suffix=".db")
        os.close(fd)
        init_release_relationship_schema(self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                # On Windows, sqlite file handles can be released slightly after context exit.
                pass

    def _count_rows(self, table: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def test_schema_init_is_idempotent(self) -> None:
        init_release_relationship_schema(self.db_path)
        init_release_relationship_schema(self.db_path)
        with sqlite3.connect(self.db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertIn("release_dependencies", tables)
        self.assertIn("release_co_releases", tables)

    def test_save_is_idempotent_and_deduplicated(self) -> None:
        active = ["A", "B", "C"]
        save_release_relationship_updates(
            selected_release_ids=["A"],
            depends_on_ids=["B", "B"],
            depended_by_ids=[],
            co_release_ids=["C", "C"],
            active_release_ids=active,
            db_path=self.db_path,
        )
        first_dep = self._count_rows("release_dependencies")
        first_co = self._count_rows("release_co_releases")

        save_release_relationship_updates(
            selected_release_ids=["A"],
            depends_on_ids=["B", "B"],
            depended_by_ids=[],
            co_release_ids=["C", "C"],
            active_release_ids=active,
            db_path=self.db_path,
        )
        second_dep = self._count_rows("release_dependencies")
        second_co = self._count_rows("release_co_releases")

        self.assertEqual(first_dep, second_dep)
        self.assertEqual(first_co, second_co)

    def test_corelease_symmetry_is_enforced(self) -> None:
        active = ["A", "B"]
        save_release_relationship_updates(
            selected_release_ids=["A"],
            depends_on_ids=[],
            depended_by_ids=[],
            co_release_ids=["B"],
            active_release_ids=active,
            db_path=self.db_path,
        )
        maps = get_release_relationship_maps(active, db_path=self.db_path)
        self.assertIn("B", maps["co_releases"]["A"])
        self.assertIn("A", maps["co_releases"]["B"])

    def test_retrieval_filters_to_active_ids(self) -> None:
        active = ["A", "B", "C", "D"]
        save_release_relationship_updates(
            selected_release_ids=["A", "D"],
            depends_on_ids=["B", "C"],
            depended_by_ids=[],
            co_release_ids=["C"],
            active_release_ids=active,
            db_path=self.db_path,
        )

        maps = get_release_relationship_maps(["A", "B", "C"], db_path=self.db_path)
        self.assertIn("A", maps["dependencies"])
        self.assertNotIn("D", maps["dependencies"])
        self.assertNotIn("D", maps["co_releases"])

    def test_reconcile_removes_stale_edges(self) -> None:
        active = ["A", "B", "C"]
        save_release_relationship_updates(
            selected_release_ids=["A", "B"],
            depends_on_ids=["B", "C"],
            depended_by_ids=[],
            co_release_ids=["C"],
            active_release_ids=active,
            db_path=self.db_path,
        )

        metrics = reconcile_release_relationships(["A", "B"], db_path=self.db_path)
        self.assertGreaterEqual(metrics["dependencies_removed"], 0)
        self.assertGreaterEqual(metrics["coreleases_removed"], 0)

        maps = get_release_relationship_maps(["A", "B"], db_path=self.db_path)
        flattened = [target for values in maps["dependencies"].values() for target in values]
        self.assertNotIn("C", flattened)

    def test_depended_by_ids_create_incoming_dependencies(self) -> None:
        active = ["A", "B", "C"]
        save_release_relationship_updates(
            selected_release_ids=["A"],
            depends_on_ids=[],
            depended_by_ids=["B", "C"],
            co_release_ids=[],
            active_release_ids=active,
            db_path=self.db_path,
        )

        maps = get_release_relationship_maps(active, db_path=self.db_path)
        self.assertIn("A", maps["dependencies"]["B"])
        self.assertIn("A", maps["dependencies"]["C"])


if __name__ == "__main__":
    unittest.main()
