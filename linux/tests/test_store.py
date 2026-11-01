import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import TaskStore


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = TaskStore(Path(self.dir.name) / "tasks.db")

    def tearDown(self):
        self.store.close()
        self.dir.cleanup()

    def test_create_complete_reopen_delete(self):
        key = self.store.add_task("  Build native apps  ", priority=1, due_date="2026-11-02")
        rows = self.store.list_tasks()
        self.assertEqual(rows[0]["title"], "Build native apps")
        self.assertEqual(rows[0]["priority"], 1)
        self.assertTrue(self.store.complete_task(key, True))
        self.assertEqual(self.store.list_tasks(), [])
        self.assertEqual(len(self.store.list_tasks(include_completed=True)), 1)
        self.assertTrue(self.store.complete_task(key, False))
        self.assertEqual(len(self.store.list_tasks()), 1)
        self.assertTrue(self.store.rename_task(key, "Updated title"))
        self.assertEqual(self.store.list_tasks()[0]["title"], "Updated title")
        self.assertTrue(self.store.delete_task(key))
        self.assertFalse(self.store.delete_task(key))

    def test_validation_and_project_relationship(self):
        with self.assertRaises(ValueError):
            self.store.add_task(" ")
        with self.assertRaises(ValueError):
            self.store.add_task("valid", priority=5)
        with self.assertRaises(ValueError):
            self.store.add_task("valid", due_date="2026-02-30")
        with self.assertRaises(ValueError):
            self.store.add_task("valid", due_date="2026-13-01")
        project = self.store.add_project("Personal")
        task = self.store.add_task("Write roadmap", project_id=project)
        self.assertEqual(self.store.list_tasks()[0]["project_id"], project)
        self.assertEqual(self.store.list_projects()[0]["id"], project)
        with self.assertRaises(Exception):
            self.store.add_task("Invalid project", project_id="missing")

    def test_rejects_invalid_field_types_and_unpaired_unicode(self):
        bad_cases = [
            {"title": None},
            {"title": 4},
            {"title": "safe", "priority": True},
            {"title": "safe", "priority": 1.0},
            {"title": "safe", "due_date": 20261031},
            {"title": "broken " + chr(0xD800)},
        ]
        for case in bad_cases:
            with self.subTest(case=repr(case)):
                with self.assertRaises(ValueError):
                    self.store.add_task(**case)
        for name in (None, 4, "bad " + chr(0xD800)):
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValueError):
                    self.store.add_project(name)
        task_id = self.store.add_task("safe")
        with self.assertRaises(ValueError):
            self.store.rename_task(task_id, "bad " + chr(0xD800))
        self.assertEqual(self.store.list_tasks()[0]["title"], "safe")
        self.assertEqual(len(self.store.list_tasks()), 1)

    def test_views_and_literal_search(self):
        project = self.store.add_project("Launch")
        self.store.add_task("Overdue % report", priority=1, due_date="2026-10-30")
        self.store.add_task("This week", due_date="2026-11-04", project_id=project)
        self.store.add_task("Unscheduled")
        completed = self.store.add_task("Finished")
        self.store.complete_task(completed, True)
        self.assertEqual([t["title"] for t in self.store.list_tasks(view="Today", today="2026-10-31")], ["Overdue % report"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(view="Upcoming", today="2026-10-31")], ["This week"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(view="Priority")], ["Overdue % report"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(view="Completed")], ["Finished"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(view="Project", project_id=project)], ["This week"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(view="Project", project_id=None)], ["Overdue % report", "Unscheduled"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(query="%")], ["Overdue % report"])
        self.assertEqual(self.store.list_tasks(query="_"), [])
        with self.assertRaises(ValueError):
            self.store.list_tasks(view="INVALID")

    def test_private_database_file_and_symlink_guard(self):
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        linked = Path(self.dir.name) / "alias.sqlite3"
        linked.symlink_to(self.store.path)
        with self.assertRaises(ValueError):
            TaskStore(linked)

    def test_data_persists_after_clean_restart(self):
        self.store.add_task("Save across restarts", priority=2)
        self.store.close()
        self.store = TaskStore(Path(self.dir.name) / "tasks.db")
        self.assertEqual(self.store.list_tasks()[0]["title"], "Save across restarts")


if __name__ == "__main__":
    unittest.main()
