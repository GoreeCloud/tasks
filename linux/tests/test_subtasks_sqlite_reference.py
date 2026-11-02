"""Disposable SQLite test: partial failures cannot commit a subtree mutation."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import BackupError
from subtasks_sqlite_reference import InMemorySubtreeReference

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/portable/schema4-proposed-synthetic.json"
WHEN = "2026-11-02T14:00:00Z"


class TransactionReferenceTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.repository = InMemorySubtreeReference(self.db)
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.repository.seed(self.fixture)

    def tearDown(self):
        self.db.close()

    def test_full_group_roundtrip_preserves_each_task_and_exact_metadata(self):
        ids = self.repository.delete_subtree("task-notes", WHEN, "whole")
        self.assertEqual(len(ids), 3)
        self.assertEqual(self.repository.workspace()["tasks"], [])
        self.assertEqual(len(self.repository.trash()), 3)
        self.assertEqual(len(self.repository.manifests()["whole"]["memberIds"]), 3)
        self.repository.restore_group("whole")
        self.assertEqual(self.repository.manifests(), {})
        self.assertEqual(self.repository.workspace(), self.fixture)
        self.assertEqual(self.repository.trash(), [])

    def test_partial_group_and_stale_parent_cannot_restore(self):
        self.repository.delete_subtree("task-empty-notes", WHEN, "child")
        self.assertEqual(len(self.repository.workspace()["tasks"]), 1)
        self.db.execute("DELETE FROM proposed_trash WHERE id='task-grandchild'")
        self.db.commit()
        before = deepcopy((self.repository.workspace(), self.repository.trash()))
        with self.assertRaises(BackupError):
            self.repository.restore_group("child")
        self.assertEqual((self.repository.workspace(), self.repository.trash()), before)

    def test_mid_delete_sqlite_fault_rolls_back_all_rows(self):
        self.db.execute("""
            CREATE TRIGGER injection AFTER INSERT ON proposed_trash
            WHEN NEW.id='task-grandchild'
            BEGIN SELECT RAISE(ABORT,'injected delete crash'); END
        """)
        before = deepcopy((self.repository.workspace(), self.repository.trash()))
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.delete_subtree("task-notes", WHEN, "whole")
        self.assertEqual((self.repository.workspace(), self.repository.trash()), before)
        self.assertEqual(self.repository.manifests(), {})

    def test_mid_restore_sqlite_fault_rolls_back_all_rows(self):
        self.repository.delete_subtree("task-notes", WHEN, "whole")
        self.db.execute("""
            CREATE TRIGGER injection AFTER INSERT ON proposed_tasks
            WHEN NEW.id='task-grandchild'
            BEGIN SELECT RAISE(ABORT,'injected restore crash'); END
        """)
        before = deepcopy((self.repository.workspace(), self.repository.trash()))
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.restore_group("whole")
        self.assertEqual((self.repository.workspace(), self.repository.trash()), before)
        self.assertIn("whole", self.repository.manifests())

    def test_missing_leaf_with_forged_group_counts_cannot_restore(self):
        self.repository.delete_subtree("task-notes", WHEN, "whole")
        manifest = deepcopy(self.repository.manifests()["whole"])
        self.db.execute("DELETE FROM proposed_trash WHERE id='task-grandchild'")
        self.db.execute("UPDATE proposed_trash SET group_size=2 WHERE group_id='whole'")
        self.db.commit()
        before = deepcopy((self.repository.workspace(), self.repository.trash()))
        with self.assertRaises(BackupError):
            self.repository.restore_group("whole")
        self.assertEqual((self.repository.workspace(), self.repository.trash()), before)
        self.assertEqual(self.repository.manifests()["whole"], manifest)

    def test_interdependent_groups_restore_only_after_missing_parent_returns(self):
        self.repository.delete_subtree("task-empty-notes", WHEN, "child")
        self.repository.delete_subtree("task-notes", WHEN, "root")
        self.assertEqual(set(self.repository.manifests()), {"child", "root"})
        before = deepcopy((self.repository.workspace(), self.repository.trash(),
                           self.repository.manifests()))
        with self.assertRaises(BackupError):
            self.repository.restore_group("child")
        self.assertEqual((self.repository.workspace(), self.repository.trash(),
                          self.repository.manifests()), before)
        self.repository.restore_group("root")
        self.repository.restore_group("child")
        self.assertEqual(self.repository.workspace(), self.fixture)
        self.assertEqual(self.repository.trash(), [])
        self.assertEqual(self.repository.manifests(), {})

    def test_rejects_disk_database_before_creating_any_tables(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "personal.sqlite3"
            connection = sqlite3.connect(path)
            try:
                with self.assertRaises(ValueError):
                    InMemorySubtreeReference(connection)
                tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                self.assertEqual(tables, [])
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
