import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import BackupError, export_data, export_file, import_data, read_backup, serialized, validate
from store import TaskStore


class PortableBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.source = TaskStore(self.folder / "source.sqlite3")
        self.target = TaskStore(self.folder / "target.sqlite3")

    def tearDown(self):
        self.source.close()
        self.target.close()
        self.temp.cleanup()

    def create_fixture(self):
        project_id = self.source.add_project("GoreeCloud Tasks")
        self.source.add_task("Ready for release", priority=1, due_date="2026-11-06", project_id=project_id)
        completed = self.source.add_task("Validated backup", priority=4)
        self.source.complete_task(completed, True)

    def test_legacy_sqlite_description_columns_migrate_without_data_loss(self):
        old = self.folder / "old-tasks.sqlite3"
        connection = sqlite3.connect(old)
        try:
            connection.execute("CREATE TABLE projects (id TEXT PRIMARY KEY,name TEXT NOT NULL)")
            connection.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY,title TEXT NOT NULL,priority INTEGER NOT NULL,"
                               "due_date TEXT,project_id TEXT,completed INTEGER NOT NULL,created_at TEXT NOT NULL,completed_at TEXT)")
            connection.execute("CREATE TABLE deleted_tasks (id TEXT PRIMARY KEY,title TEXT NOT NULL,priority INTEGER NOT NULL,"
                               "due_date TEXT,project_id TEXT,completed INTEGER NOT NULL,created_at TEXT NOT NULL,completed_at TEXT,deleted_at TEXT NOT NULL)")
            connection.execute("INSERT INTO tasks(id,title,priority,completed,created_at) "
                               "VALUES ('legacy-active','Original',2,0,'2026-10-31T12:00:00Z')")
            connection.execute("INSERT INTO deleted_tasks(id,title,priority,completed,created_at,deleted_at) "
                               "VALUES ('legacy-trash','Recoverable',4,0,'2026-10-31T12:00:00Z','2026-11-01T12:00:00Z')")
            connection.commit()
        finally:
            connection.close()
        store = TaskStore(old)
        try:
            self.assertEqual(store.list_tasks()[0]["title"], "Original")
            self.assertEqual(store.list_tasks()[0]["description"], "")
            self.assertEqual(store.list_deleted_tasks()[0]["description"], "")
            self.assertTrue(store.restore_deleted_task("legacy-trash"))
            store.update_task("legacy-active",title="Original",priority=2,description="New notes after migration")
            self.assertEqual(export_data(store)["schema"],2)
            store.bulk_edit_tasks(["legacy-active"], "trash")
            self.assertEqual(store.list_deleted_tasks()[0]["description"],"New notes after migration")
        finally:
            store.close()
        # Opening twice must not create duplicate columns or change notes.
        store = TaskStore(old)
        try:
            self.assertEqual(store.list_deleted_tasks()[0]["description"],"New notes after migration")
        finally:
            store.close()

    def test_proposed_schema4_is_rejected_without_changing_empty_store(self):
        fixture=json.loads((Path(__file__).resolve().parents[2] /
                            "fixtures/portable/schema4-proposed-synthetic.json").read_text(encoding="utf-8"))
        with self.assertRaises(BackupError):
            validate(fixture)
        with self.assertRaises(BackupError):
            import_data(self.target,fixture)
        self.assertEqual(self.target.list_tasks(view="All"),[])

    def test_schema3_labels_import_export_and_atomic_trash(self):
        fixture = json.loads((Path(__file__).resolve().parents[2] /
                              "fixtures/portable/schema3-synthetic.json").read_text(encoding="utf-8"))
        self.assertEqual(validate(fixture),fixture)
        with self.assertRaises(BackupError):
            validate(dict(fixture,schema=2))
        broken = json.loads(json.dumps(fixture))
        broken["tasks"][0]["labels"] = ["Work","Work"]
        with self.assertRaises(BackupError):
            validate(broken)
        tasks, projects = import_data(self.target,fixture)
        self.assertEqual((tasks,projects),(2,1))
        exported = export_data(self.target)
        self.assertEqual(exported["schema"],3)
        self.assertEqual({t["id"]:t["labels"] for t in exported["tasks"]},
                         {t["id"]:t["labels"] for t in fixture["tasks"]})
        self.assertTrue(self.target.delete_task("task-notes"))
        self.assertEqual(json.loads(self.target.list_deleted_tasks()[0]["labels_json"]),["Work","Design 🧭"])
        self.assertTrue(self.target.restore_deleted_task("task-notes"))
        copied=self.target.duplicate_task("task-notes")
        row=next(t for t in self.target.list_tasks(include_completed=True) if t["id"]==copied)
        self.assertEqual(json.loads(row["labels_json"]),["Work","Design 🧭"])
        self.assertTrue(self.target.update_task(copied,title="Review release",priority=1,labels=["Archive"]))
        with self.assertRaises(ValueError):
            self.target.update_task(copied,title="Review release",priority=1,labels=["A","A"])
        self.assertEqual(json.loads(next(t for t in self.target.list_tasks(include_completed=True)
                                         if t["id"]==copied)["labels_json"]),["Archive"])

    def test_schema2_descriptions_round_trip_across_trash_and_restore(self):
        fixture = json.loads((Path(__file__).resolve().parents[2] /
                              "fixtures/portable/schema2-synthetic.json").read_text(encoding="utf-8"))
        self.assertEqual(validate(fixture), fixture)
        count, _ = import_data(self.target, fixture)
        self.assertEqual(count, 2)
        imported = self.target.list_tasks(include_completed=True)
        self.assertEqual(next(t for t in imported if t["id"] == "task-notes")["description"], "Check accessibility 🧭\nFollow up on copy edits.")
        exported = export_data(self.target)
        self.assertEqual(exported["schema"], 2)
        self.assertEqual(next(t for t in exported["tasks"] if t["id"] == "task-notes")["description"], fixture["tasks"][0]["description"])
        self.assertTrue(self.target.delete_task("task-notes"))
        self.assertEqual(self.target.list_deleted_tasks()[0]["description"], fixture["tasks"][0]["description"])
        self.assertTrue(self.target.restore_deleted_task("task-notes"))
        self.assertEqual(next(t for t in self.target.list_tasks(include_completed=True) if t["id"] == "task-notes")["description"], fixture["tasks"][0]["description"])
        broken = json.loads(json.dumps(fixture))
        broken["tasks"][0]["description"] = "🧭" * 1001
        with self.assertRaises(BackupError):
            validate(broken)
        legacy = json.loads((Path(__file__).resolve().parents[2] /
                             "fixtures/portable/schema1-synthetic.json").read_text(encoding="utf-8"))
        self.assertEqual(validate(legacy), legacy)

    def test_strict_timestamp_contract_prevents_cross_platform_restore_failure(self):
        matrix = json.loads((Path(__file__).resolve().parents[2] /
                             "fixtures/portable/timestamp-contract.json").read_text(encoding="utf-8"))
        fixture = json.loads((Path(__file__).resolve().parents[2] /
                              "fixtures/portable/schema1-synthetic.json").read_text(encoding="utf-8"))
        for timestamp in matrix["valid"]:
            with self.subTest(valid=timestamp):
                snapshot = json.loads(json.dumps(fixture))
                snapshot["tasks"][0]["createdAt"] = timestamp
                self.assertEqual(validate(snapshot)["tasks"][0]["createdAt"], timestamp)
        for timestamp in matrix["invalid"]:
            with self.subTest(invalid=timestamp):
                snapshot = json.loads(json.dumps(fixture))
                snapshot["tasks"][0]["createdAt"] = timestamp
                with self.assertRaises(BackupError):
                    import_data(self.target, snapshot)
                self.assertEqual(self.target.list_tasks(include_completed=True), [])
                self.assertEqual(self.target.list_projects(), [])

    def test_shared_portable_fixture_and_fail_closed_variants(self):
        fixture = Path(__file__).resolve().parents[2] / "fixtures/portable/schema1-synthetic.json"
        original = json.loads(fixture.read_text(encoding="utf-8"))
        verified = read_backup(fixture)
        self.assertEqual(verified, original)
        self.assertEqual(import_data(self.target, verified), (3, 2))
        restored = export_data(self.target)
        self.assertEqual(sorted(restored["tasks"], key=lambda t: t["id"]),
                         sorted(original["tasks"], key=lambda t: t["id"]))
        self.assertEqual(sorted(restored["projects"], key=lambda t: t["id"]),
                         sorted(original["projects"], key=lambda t: t["id"]))
        self.assertEqual(validate(json.loads(serialized(restored))), restored)
        completed = next(task for task in restored["tasks"] if task["id"] == "task-completed")
        self.assertEqual(completed["completedAt"], "2026-11-01T01:23:45.654321Z")
        self.assertEqual(completed["createdAt"], "2026-10-31T20:15:42.123456-05:00")

        rejected = [
            {**original, "projects": []},
            {**original, "tasks": [{**original["tasks"][0], "completedAt": None}]},
            {**original, "tasks": [{**original["tasks"][0], "priority": True}]},
            {**original, "tasks": [{**original["tasks"][0], "due": "2026-02-30"}]},
        ]
        for invalid in rejected:
            with self.subTest(invalid=invalid), self.assertRaises(BackupError):
                validate(invalid)

    def test_portable_backup_excludes_local_trash_but_preserves_active_rows(self):
        deleted_id = self.source.add_task("Recoverable but local only")
        active_id = self.source.add_task("Keep in the portable backup")
        self.assertTrue(self.source.delete_task(deleted_id))
        exported = export_data(self.source)
        self.assertEqual([task["id"] for task in exported["tasks"]], [active_id])
        self.assertEqual(len(self.source.list_deleted_tasks()), 1)
        self.assertEqual(import_data(self.target, exported), (1, 0))
        self.assertEqual(self.target.list_deleted_tasks(), [])
        self.assertEqual(self.target.list_tasks()[0]["id"], active_id)
        # Restoring local Trash does not rewrite previously exported backups.
        self.assertTrue(self.source.restore_deleted_task(deleted_id))
        self.assertEqual([task["id"] for task in exported["tasks"]], [active_id])

    def test_empty_active_workspace_with_trash_cannot_accept_restore(self):
        gone_id = self.source.add_task("Recoverable history")
        self.assertTrue(self.source.delete_task(gone_id))
        self.assertEqual(self.source.list_tasks(include_completed=True), [])
        self.assertEqual(self.source.list_projects(), [])
        backup = {
            "schema": 1, "projects": [], "tasks": [{
                "id": gone_id, "title": "Potential collision",
                "projectId": None, "due": "", "priority": 4, "completed": False,
                "createdAt": "2026-11-01T12:00:00Z", "completedAt": None
            }]
        }
        with self.assertRaisesRegex(BackupError, "including local Trash"):
            import_data(self.source, backup)
        self.assertEqual(self.source.list_tasks(include_completed=True), [])
        self.assertEqual(self.source.list_deleted_tasks()[0]["id"], gone_id)

    def test_roundtrip_without_data_loss(self):
        self.create_fixture()
        path = self.folder / "portable.json"
        size = export_file(self.source, path)
        self.assertGreater(size, 100)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        payload = read_backup(path)
        self.assertEqual(set(payload), {"schema", "projects", "tasks"})
        self.assertEqual(import_data(self.target, payload), (2, 1))
        self.assertEqual(export_data(self.target), export_data(self.source))
        self.assertEqual(len(self.target.list_tasks(view="Completed")), 1)

    def test_browser_schema_accepts_linux_export(self):
        import shutil
        if not shutil.which("node"):
            self.skipTest("Node runtime is needed for cross-format verification")
        self.create_fixture()
        path = self.folder / "browser-compatible.json"
        export_file(self.source, path)
        script = """import {readFileSync} from 'node:fs';
import {validateBackupText} from './web/backup.mjs';
const data = validateBackupText(readFileSync(process.argv[1],'utf8'));
if (data.tasks.length !== 2 || data.projects.length !== 1) process.exit(3);"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script, str(path)],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_overwrite_of_existing_backups_or_tasks(self):
        self.create_fixture()
        path = self.folder / "portable.json"
        export_file(self.source, path)
        with self.assertRaises(BackupError):
            export_file(self.source, path)
        self.target.add_task("Never discard me")
        with self.assertRaises(BackupError):
            import_data(self.target, read_backup(path))
        self.assertEqual(self.target.list_tasks()[0]["title"], "Never discard me")

    def test_refuses_symlink_destination_without_changing_target(self):
        self.create_fixture()
        victim = self.folder / "victim"
        victim.write_text("DO NOT REPLACE", encoding="utf-8")
        (self.folder / "portable.json").symlink_to(victim)
        with self.assertRaises(BackupError):
            export_file(self.source, self.folder / "portable.json")
        self.assertEqual(victim.read_text(encoding="utf-8"), "DO NOT REPLACE")

    def test_bad_records_are_rejected_without_partial_import(self):
        self.create_fixture()
        original = export_data(self.source)
        cases = [
            dict(original, schema=2),
            dict(original, tasks=[dict(original["tasks"][0], due="2026-02-30")]),
            dict(original, tasks=[dict(original["tasks"][0], projectId="unknown")]),
            dict(original, tasks=[dict(original["tasks"][0], priority=True)]),
            dict(original, tasks=[dict(original["tasks"][0], completed=True, completedAt=None)]),
            dict(original, projects=original["projects"] * 2),
            dict(original, tasks=original["tasks"] * 2)
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(BackupError):
                    import_data(self.target, case)
                self.assertEqual(self.target.list_tasks(include_completed=True), [])
                self.assertEqual(self.target.list_projects(), [])

    def test_invalid_unicode_and_unhashable_project_ids_do_not_import(self):
        self.create_fixture()
        original = export_data(self.source)
        broken = "bad " + chr(0xD800)
        cases = [
            dict(original, tasks=[dict(original["tasks"][0], title=broken)]),
            dict(original, tasks=[dict(original["tasks"][0], id=broken)]),
            dict(original, projects=[dict(original["projects"][0], name=broken)]),
            dict(original, tasks=[dict(original["tasks"][0], projectId=["invalid"])]),
        ]
        for case in cases:
            with self.subTest(case=repr(case)):
                with self.assertRaises(BackupError):
                    import_data(self.target, case)
                self.assertEqual(self.target.list_tasks(include_completed=True), [])
                self.assertEqual(self.target.list_projects(), [])

    def test_oversize_truncated_or_non_utf8_rejected(self):
        path = self.folder / "bad.json"
        for body in (b"{" + b" " * (2 * 1024 * 1024), b"\xff", b"{"):
            path.write_bytes(body)
            with self.assertRaises(BackupError):
                read_backup(path)

    def test_export_refuses_missing_database(self):
        target = self.folder / "no-such-database.sqlite3"
        json_file = self.folder / "snapshot.json"
        repo_backup = Path(__file__).resolve().parents[1] / "backup.py"
        result = subprocess.run(
            [sys.executable, str(repo_backup), "--database", str(target), "export", "--file", str(json_file)],
            capture_output=True, text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json_file.exists())
        self.assertFalse(target.exists())

    def test_portable_cli_in_empty_target(self):
        self.create_fixture()
        json_file = self.folder / "snapshot.json"
        repo_backup = Path(__file__).resolve().parents[1] / "backup.py"
        exported = subprocess.run(
            [sys.executable, str(repo_backup), "--database", str(self.source.path), "export", "--file", str(json_file)],
            capture_output=True, text=True
        )
        self.assertEqual(exported.returncode, 0, exported.stderr)
        imported = subprocess.run(
            [sys.executable, str(repo_backup), "--database", str(self.target.path), "import", "--file", str(json_file)],
            capture_output=True, text=True
        )
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(export_data(self.source), export_data(self.target))


if __name__ == "__main__":
    unittest.main()
