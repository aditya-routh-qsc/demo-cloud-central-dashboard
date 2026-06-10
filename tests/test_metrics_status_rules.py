from __future__ import annotations

import unittest

from database import _is_active_ticket_status


class MetricsStatusRulesTests(unittest.TestCase):
    def test_excludes_done_rejected_and_todo_variants(self) -> None:
        self.assertFalse(_is_active_ticket_status("Done"))
        self.assertFalse(_is_active_ticket_status("rejected"))
        self.assertFalse(_is_active_ticket_status("To Do"))
        self.assertFalse(_is_active_ticket_status("SQA To Do"))

    def test_includes_in_progress_and_empty_status(self) -> None:
        self.assertTrue(_is_active_ticket_status("In Progress"))
        self.assertTrue(_is_active_ticket_status("Needs Review"))
        self.assertTrue(_is_active_ticket_status(""))
        self.assertTrue(_is_active_ticket_status(None))


if __name__ == "__main__":
    unittest.main()
