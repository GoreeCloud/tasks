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
