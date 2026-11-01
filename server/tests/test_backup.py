"""Offline-only snapshot tests with disposable databases and synthetic task data."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import TaskDatabase
from backup import SnapshotError, restore_to_new_database, snapshot_database


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "live.sqlite3"
        self.store = TaskDatabase(self.source)
        self.created = self.store.create_task(
            {"title": "Recoverable task", "priority": 2},
            "snapshot-test-mutation-0001"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_live_database_snapshot_and_recovery_roundtrip(self):
        backup = self.root / "backup.sqlite3"
        recovered = self.root / "recovered.sqlite3"
        self.assertGreater(snapshot_database(self.source, backup), 100)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertGreater(restore_to_new_database(backup, recovered), 100)
        self.assertEqual(recovered.stat().st_mode & 0o777, 0o600)
        restored = TaskDatabase(recovered)
        self.assertEqual(restored.list_tasks()[0]["id"], self.created["id"])
        self.assertEqual(restored.changes()["changes"][0]["task"]["title"], "Recoverable task")
        replay = restored.create_task(
            {"title": "Recoverable task", "priority": 2},
            "snapshot-test-mutation-0001"
        )
        self.assertEqual(replay["id"], self.created["id"])
        self.assertEqual(len(restored.list_tasks()), 1)

    def test_snapshot_consistent_after_source_changes(self):
        backup = self.root / "backup.sqlite3"
        snapshot_database(self.source, backup)
        self.store.update_task(self.created["id"], {"title": "Changed later"}, 1)
        restored = TaskDatabase(backup)
        self.assertEqual(restored.get_task(self.created["id"])["title"], "Recoverable task")
        self.assertEqual(len(restored.changes()["changes"]), 1)

    def test_refuses_overwrite_and_symlinks(self):
        backup = self.root / "backup.sqlite3"
        snapshot_database(self.source, backup)
        with self.assertRaises(SnapshotError):
            snapshot_database(self.source, backup)
        victim = self.root / "untouched"
        victim.write_text("DO NOT TOUCH", encoding="utf-8")
        alias = self.root / "alias.sqlite3"
        alias.symlink_to(victim)
        with self.assertRaises(SnapshotError):
            snapshot_database(self.source, alias)
        with self.assertRaises(SnapshotError):
            snapshot_database(alias, self.root / "new.sqlite3")
        self.assertEqual(victim.read_text(encoding="utf-8"), "DO NOT TOUCH")

    def test_invalid_or_missing_source_does_not_create_destination(self):
        fake = self.root / "garbage.sqlite3"
        fake.write_bytes(b"not a valid SQLite database")
        destination = self.root / "never-created.sqlite3"
        with self.assertRaises(SnapshotError):
            snapshot_database(fake, destination)
        self.assertFalse(destination.exists())
        with self.assertRaises(SnapshotError):
            restore_to_new_database(self.root / "missing.sqlite3", destination)
        self.assertFalse(destination.exists())

    def test_refuses_database_with_unrecognized_schema(self):
        foreign = self.root / "foreign.sqlite3"
        with sqlite3.connect(foreign) as connection:
            connection.execute("CREATE TABLE unrelated(id INTEGER)")
        with self.assertRaises(SnapshotError):
            restore_to_new_database(foreign, self.root / "out.sqlite3")
        self.assertFalse((self.root / "out.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
