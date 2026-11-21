"""Native Linux backend logic tests; no filesystem changes or real API traffic."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QCoreApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import TasksBackend  # noqa: E402


class TasksBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.backend = TasksBackend("http://127.0.0.1:8000",
                                    "mock-token-only-for-unittest-not-real-12345")
        today = date.today()
        self.backend._all_tasks = [
            dict(id="1", title="Pay rent", description="", tags=["home"],
                 project_id="p", due_date=today.isoformat(), completed_at=None),
            dict(id="2", title="Read book", description="Work notes", tags=["work"],
                 project_id="q", due_date=(today + timedelta(days=3)).isoformat(),
                 completed_at=None),
            dict(id="3", title="Past task", description="", tags=["home"],
                 project_id="p", due_date=(today - timedelta(days=3)).isoformat(),
                 completed_at="2026-11-20T00:00:00Z"),
            dict(id="4", title="No deadline", description="", tags=[],
                 project_id=None, due_date=None, completed_at=None),
        ]
        self.backend._apply_filters()

    def test_filter_status_date_and_project(self):
        self.assertEqual(len(self.backend.tasks), 3)
        self.backend.setView("today")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["1"])
        self.backend.setView("upcoming")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["2"])
        self.backend.setView("completed")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["3"])
        self.backend.setView("inbox")
        self.backend.setProjectFilter("p")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["1"])

    def test_search_and_invalid_view(self):
        self.backend.setSearch("HOME")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["1"])
        self.backend.setSearch("work notes")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["2"])
        self.backend.setView("no-such-view")
        self.assertEqual(self.backend.error, "Unknown task view")

    def test_task_fields_reject_bad_inputs(self):
        mk = TasksBackend._task_data
        value = mk(" Task ", "notes", 2, "2026-11-21", "weekly", "", "Home,home")
        self.assertEqual(value["tags"], ["home"])
        self.assertEqual(value["title"], "Task")
        self.assertIsNone(value["project_id"])
        for args in [
            (" ", "", 2, "", "none", "", ""),
            ("Hi", "", 8, "", "none", "", ""),
            ("Hi", "", 2, "", "daily", "", ""),
            ("Hi", "", 2, "2026-02-30", "none", "", ""),
            ("Hi", "", 2, "", "bogus", "", ""),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                mk(*args)


if __name__ == "__main__":
    unittest.main()
