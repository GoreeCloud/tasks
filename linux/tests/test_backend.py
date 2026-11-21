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

    def test_habit_response_and_empty_model(self):
        self.assertEqual(self.backend.habits, [])
        sample = {"id": "fixture", "name": "Read", "checked_in_today": False,
                  "current_streak": 3, "total_checkins": 7, "version": 2}
        self.backend._update_habits([sample])
        self.assertEqual(self.backend.habits[0]["current_streak"], 3)
        self.backend._update_habits({"bad": "shape"})
        self.assertEqual(self.backend.error, "Invalid habit list response")
        self.assertEqual(self.backend.habits[0]["name"], "Read")

    def test_task_fields_reject_bad_inputs(self):
        mk = TasksBackend._task_data
        value = mk(" Task ", "notes", 2, "2026-11-21", "weekly", "", "Home,home")
        self.assertEqual(value["tags"], ["home"])
        self.assertEqual(value["title"], "Task")
        subtask = mk("Child", "", 2, "", "none", "", "", "existing-parent-id")
        self.assertEqual(subtask["parent_id"], "existing-parent-id")
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



    def test_consistent_snapshot_full_and_fail_closed(self):
        base = dict(id="placeholder", title="Private", description="", tags=[],
                    project_id="project-1", due_date=None, completed_at=None)
        tasks = [{**base, "id": f"synthetic-{i}", "title": f"Task {i}"} for i in range(1005)]
        snapshot = dict(format="goreecloud-tasks-sync-1", cursor=42,
                        tasks=tasks, projects=[dict(id="project-1", name="Testing")])
        self.backend._apply_snapshot(snapshot)
        self.assertEqual(len(self.backend.tasks), 1005)
        self.assertEqual(len(self.backend.allTasks), 1005)
        self.assertEqual(self.backend.projects[0]["name"], "Testing")

        previous = list(self.backend.allTasks)
        previous_projects = list(self.backend.projects)
        for invalid in [
            None,
            dict(format="unknown", cursor=42, tasks=tasks, projects=[]),
            dict(format="goreecloud-tasks-sync-1", cursor=-1, tasks=[], projects=[]),
            dict(format="goreecloud-tasks-sync-1", cursor=42, tasks=tasks, projects=[{"id": 7}]),
            dict(format="goreecloud-tasks-sync-1", cursor=42, tasks=tasks + [None], projects=[]),
            dict(format="goreecloud-tasks-sync-1", cursor=42,
                 tasks=tasks * 6, projects=[]),
        ]:
            with self.subTest(invalid_type=type(invalid).__name__):
                self.backend._apply_snapshot(invalid)
                self.assertEqual(self.backend.allTasks, previous)
                self.assertEqual(self.backend.projects, previous_projects)

    def test_refresh_uses_single_atomic_bootstrap_request(self):
        calls = []
        self.backend._request = lambda method, path, callback=None: calls.append(
            (method, path, callback)
        )
        self.backend.refresh()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0:2], ("GET", "/sync/bootstrap"))
        self.assertEqual(calls[0][2], self.backend._apply_snapshot)

if __name__ == "__main__":
    unittest.main()
