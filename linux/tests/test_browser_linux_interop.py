"""Synthetic actual-JavaScript browser export -> native Linux SQLite -> browser validation.

Only disposable local task fixtures; no personal data, browsers, network, or
Android compatibility claim. Run with Python 3 and Node 22+.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "linux"))
from backup import export_data, import_data, validate
from store import TaskStore

NODE = shutil.which("node")

EXPORT_JS = """
import { exportBackup } from './web/backup.mjs';
let text = '';
for await (const chunk of process.stdin) text += chunk;
process.stdout.write(exportBackup(JSON.parse(text)));
"""
VALIDATE_JS = """
import { validateBackupText } from './web/backup.mjs';
let text = '';
for await (const chunk of process.stdin) text += chunk;
process.stdout.write(JSON.stringify(validateBackupText(text)));
"""


@unittest.skipUnless(NODE, "Node.js is required for real browser JavaScript interop")
class ActualJsToLinuxBackupInterop(unittest.TestCase):
    def node(self, program, text):
        result = subprocess.run(
            [NODE, "--input-type=module", "-e", program],
            input=text, text=True, capture_output=True, cwd=ROOT, timeout=12,
            check=True,
        )
        return json.loads(result.stdout)

    def fixture(self, *, description="", labels=(), schema=1):
        # Timestamp offsets and completion history must be byte-for-byte
        # portable between the JavaScript and Python validators.
        task = {
            "id": "task-fixed", "title": "Release 🚀", "projectId": "project-fixed",
            "due": "2028-02-29", "priority": 2, "completed": True,
            "createdAt": "2026-11-08T21:04:05.123456-06:00",
            "completedAt": "2026-11-09T08:09:10.654321Z",
            "description": description, "labels": list(labels),
        }
        return {"schema": schema,
                "projects": [{"id": "project-fixed", "name": "Personal"}],
                "tasks": [task]}

    def roundtrip(self, original, expected_schema):
        browser = self.node(EXPORT_JS, json.dumps(original, ensure_ascii=False))
        self.assertEqual(browser["schema"], expected_schema)
        # Strict native validator must accept exactly what the browser serialized.
        self.assertEqual(validate(browser), browser)
        with tempfile.TemporaryDirectory(prefix="gc-tasks-browser-linux-") as tmp:
            store = TaskStore(Path(tmp) / "test.sqlite")
            try:
                self.assertEqual(import_data(store, browser), (1, 1))
                linux = export_data(store)
            finally:
                store.close()
        self.assertEqual(linux["schema"], expected_schema)
        self.assertEqual(linux, browser)
        # Revalidate native output with actual browser JavaScript parser.
        parsed = self.node(VALIDATE_JS, json.dumps(linux, ensure_ascii=False))
        self.assertEqual(parsed, browser)
        task = parsed["tasks"][0]
        self.assertEqual(task["createdAt"], original["tasks"][0]["createdAt"])
        self.assertEqual(task["completedAt"], original["tasks"][0]["completedAt"])
        self.assertEqual(task["projectId"], "project-fixed")

    def test_cleared_empty_label_and_description_downgrade_to_schema_one(self):
        self.roundtrip(self.fixture(), 1)

    def test_real_description_survives_schema_two_across_browser_linux(self):
        self.roundtrip(self.fixture(description="Line one\nPrivate context 🧭"), 2)

    def test_labels_and_notes_survive_schema_three_without_copies(self):
        self.roundtrip(self.fixture(description="Important", labels=["Work", "🚀"]), 3)


if __name__ == "__main__":
    unittest.main()
