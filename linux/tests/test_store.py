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
        self.assertTrue(self.store.delete_task(key))
        self.assertFalse(self.store.delete_task(key))

    def test_validation_and_project_relationship(self):
        with self.assertRaises(ValueError):
            self.store.add_task(" ")
        with self.assertRaises(ValueError):
            self.store.add_task("valid", priority=5)
        with self.assertRaises(ValueError):
            self.store.add_task("valid", due_date="2026-02-30")
        project = self.store.add_project("Personal")
        task = self.store.add_task("Write roadmap", project_id=project)
        self.assertEqual(self.store.list_tasks()[0]["project_id"], project)
        self.assertEqual(self.store.list_projects()[0]["id"], project)
        with self.assertRaises(Exception):
            self.store.add_task("Invalid project", project_id="missing")


if __name__ == "__main__":
    unittest.main()
