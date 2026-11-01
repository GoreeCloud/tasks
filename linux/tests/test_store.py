import tempfile
import unittest
import sqlite3
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

    def test_trash_survives_restart_and_restores_exact_fields(self):
        project = self.store.add_project("Roadmap")
        task_id = self.store.add_task("Review 🚀", priority=1,
                                      due_date="2026-11-09", project_id=project)
        self.store.complete_task(task_id, True)
        original = self.store.list_tasks(include_completed=True)[0]
        self.assertTrue(self.store.delete_task(task_id))
        self.assertFalse(self.store.delete_task(task_id))
        self.assertEqual(self.store.list_tasks(include_completed=True), [])
        deleted = self.store.list_deleted_tasks()
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]["id"], task_id)
        self.assertTrue(deleted[0]["deleted_at"])
        for field, value in original.items():
            self.assertEqual(deleted[0][field], value)
        self.assertEqual(len(self.store.list_deleted_tasks(query="Review")), 1)
        self.assertEqual(self.store.list_deleted_tasks(query="%"), [])
        self.store.close()
        self.store = TaskStore(Path(self.dir.name) / "tasks.db")
        self.assertEqual(self.store.list_tasks(include_completed=True), [])
        self.assertEqual(self.store.list_deleted_tasks()[0]["id"], task_id)
        self.assertTrue(self.store.restore_deleted_task(task_id))
        self.assertFalse(self.store.restore_deleted_task(task_id))
        self.assertEqual(self.store.list_deleted_tasks(), [])
        self.assertEqual(self.store.list_tasks(include_completed=True), [original])

    def test_trash_conflicts_roll_back_without_data_loss(self):
        task_id = self.store.add_task("Original record")
        self.assertTrue(self.store.delete_task(task_id))
        trashed = self.store.list_deleted_tasks()[0]
        # A restored import can later reuse the same ID; neither row should
        # be overwritten by deletion or restoration after such a collision.
        with self.store.db:
            self.store.db.execute(
                "INSERT INTO tasks (id,title,priority,created_at,completed) "
                "VALUES (?,?,?,?,?)",
                (task_id, "Different active row", 4, trashed["created_at"], 0)
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.restore_deleted_task(task_id)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.delete_task(task_id)
        self.assertEqual(self.store.list_tasks()[0]["title"], "Different active row")
        self.assertEqual(self.store.list_deleted_tasks(), [trashed])

    def test_trash_missing_project_fails_closed(self):
        project = self.store.add_project("Temporary")
        task_id = self.store.add_task("Project-bound", project_id=project)
        self.assertTrue(self.store.delete_task(task_id))
        with self.store.db:
            self.store.db.execute("DELETE FROM projects WHERE id=?", (project,))
        with self.assertRaises(ValueError):
            self.store.restore_deleted_task(task_id)
        self.assertEqual(self.store.list_tasks(include_completed=True), [])
        self.assertEqual(self.store.list_deleted_tasks()[0]["id"], task_id)

    def test_legacy_database_gains_trash_without_replacing_rows(self):
        self.store.close()
        legacy_file = Path(self.dir.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy_file) as old:
            old.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
            old.execute(
                "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, "
                "priority INTEGER, completed INTEGER, due_date TEXT, "
                "project_id TEXT, created_at TEXT, completed_at TEXT)"
            )
            old.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)",
                ("legacy-task", "Important", 2, 0, None, None,
                 "2026-10-31T10:00:00+00:00", None)
            )
        self.store = TaskStore(legacy_file)
        self.assertEqual(self.store.list_tasks()[0]["id"], "legacy-task")
        self.assertEqual(self.store.list_deleted_tasks(), [])
        self.assertTrue(self.store.delete_task("legacy-task"))
        self.assertTrue(self.store.restore_deleted_task("legacy-task"))
        self.assertEqual(self.store.list_tasks()[0]["title"], "Important")

    def test_completion_idempotency_preserves_original_timestamp(self):
        task_id = self.store.add_task("Timestamp-sensitive backup")
        self.assertFalse(self.store.complete_task(task_id, False))
        self.assertTrue(self.store.complete_task(task_id, True))
        before = self.store.list_tasks(include_completed=True)[0]["completed_at"]
        self.assertIsNotNone(before)
        self.assertFalse(self.store.complete_task(task_id, True))
        self.assertEqual(
            self.store.list_tasks(include_completed=True)[0]["completed_at"], before
        )
        for invalid in (1, 0, "true", None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.store.complete_task(task_id, invalid)
        self.assertTrue(self.store.complete_task(task_id, False))
        self.assertIsNone(self.store.list_tasks(include_completed=True)[0]["completed_at"])
        self.assertFalse(self.store.complete_task(task_id, False))
        self.assertFalse(self.store.complete_task("missing", True))

    def test_edits_priority_date_and_project_atomically(self):
        project_id = self.store.add_project("Project")
        task_id = self.store.add_task("Original", priority=4, due_date="2026-11-02")
        self.store.complete_task(task_id, True)
        before = self.store.list_tasks(include_completed=True)[0]["completed_at"]
        self.assertTrue(self.store.update_task(
            task_id, title="  Better title  ", priority=1,
            due_date="2026-12-31", project_id=project_id))
        after = self.store.list_tasks(include_completed=True)[0]
        self.assertEqual(after["title"], "Better title")
        self.assertEqual(after["priority"], 1)
        self.assertEqual(after["due_date"], "2026-12-31")
        self.assertEqual(after["project_id"], project_id)
        self.assertEqual(after["completed_at"], before)
        self.assertEqual(after["completed"], 1)
        with self.assertRaises(ValueError):
            self.store.update_task(task_id, title="No", priority=True)
        with self.assertRaises(ValueError):
            self.store.update_task(task_id, title="No", due_date="2026-02-30")
        with self.assertRaises(ValueError):
            self.store.update_task(task_id, title="No" + chr(0xD800))
        with self.assertRaises(ValueError):
            self.store.update_task(task_id, title="No", project_id=4)
        with self.assertRaises(Exception):
            self.store.update_task(task_id, title="No", project_id="missing")
        self.assertEqual(self.store.list_tasks(include_completed=True)[0]["title"], "Better title")
        self.assertFalse(self.store.update_task("missing-id", title="Valid"))

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


    def test_overdue_and_next_seven_days_calendar_boundaries(self):
        self.store.add_task("Before", priority=1, due_date="2026-10-31")
        self.store.add_task("Today", priority=2, due_date="2026-11-01")
        self.store.add_task("Sixth day", priority=3, due_date="2026-11-07")
        self.store.add_task("Seventh day", priority=4, due_date="2026-11-08")
        self.store.add_task("Unscheduled")
        finished = self.store.add_task("Completed week", due_date="2026-11-04")
        self.store.complete_task(finished, True)
        def names(view):
            return {entry["title"] for entry in self.store.list_tasks(view=view, today="2026-11-01")}
        self.assertEqual(names("Overdue"), {"Before"})
        self.assertEqual(names("Today"), {"Before", "Today"})
        self.assertEqual(names("Next 7 days"), {"Today", "Sixth day"})
        self.assertEqual(names("Upcoming"), {"Sixth day", "Seventh day"})
        self.assertEqual(
            [entry["title"] for entry in self.store.list_tasks(
                view="Next 7 days", today="2026-11-01", query="Sixth"
            )], ["Sixth day"]
        )
        with self.assertRaises(ValueError):
            self.store.list_tasks(view="Next 7 days", today="2026-11-31")

    def test_priority_filters_and_sort_modes_do_not_modify_stored_tasks(self):
        a = self.store.add_task("Zulu", priority=2, due_date="2026-11-09")
        b = self.store.add_task("Alpha", priority=3, due_date="2026-11-02")
        self.store.add_task("Undated", priority=1)
        before = self.store.list_tasks(view="All")
        self.assertEqual([t["title"] for t in self.store.list_tasks(
            view="Open", priority_filter=3)], ["Alpha"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(
            view="Open", sort_by="Due date")], ["Alpha", "Zulu", "Undated"])
        self.assertEqual([t["title"] for t in self.store.list_tasks(
            view="Open", sort_by="Title")], ["Alpha", "Undated", "Zulu"])
        for bad in (0, True, "1", 5, 1.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.store.list_tasks(priority_filter=bad)
        with self.assertRaises(ValueError):
            self.store.list_tasks(sort_by="user-supplied SQL")
        self.assertEqual(self.store.list_tasks(view="All"), before)

    def test_next_seven_days_crosses_year_boundary_without_utc_time_arithmetic(self):
        self.store.add_task("December", due_date="2026-12-31")
        self.store.add_task("January", due_date="2027-01-04")
        self.store.add_task("Beyond", due_date="2027-01-05")
        titles = {task["title"] for task in self.store.list_tasks(
            view="Next 7 days", today="2026-12-29"
        )}
        self.assertEqual(titles, {"December", "January"})

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
