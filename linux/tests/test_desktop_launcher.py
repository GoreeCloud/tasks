"""Disposable XDG desktop entry source checks; no account/OS installation."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop_launcher import create_entry, create_new_file, main, quote_exec_path


class DesktopLauncherTest(unittest.TestCase):
    def test_entry_has_safe_tokenless_exec_and_development_labels(self):
        content = create_entry(ROOT, Path(sys.executable))
        self.assertIn("[Desktop Entry]\n", content)
        self.assertIn("Name=GoreeCloud Tasks (Development Preview)", content)
        self.assertIn("Terminal=false", content)
        self.assertIn("Exec=", content)
        self.assertIn('"' + str(ROOT.resolve() / "main.py") + '"', content)
        for secret in ["GOREECLOUD_TASKS_API_TOKEN", "Bearer", "password",
                       "Icon=goreecloud", "http://"]:
            self.assertNotIn(secret, content)
        self.assertEqual(content.count("Exec="), 1)

    def test_refuses_overwrite_existing_file_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix="gc-tasks-entry-") as directory:
            root = Path(directory)
            output = root / "tasks.desktop"
            output.write_text("user-owned original", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_new_file(output, create_entry(ROOT, Path(sys.executable)))
            self.assertEqual(output.read_text(encoding="utf-8"), "user-owned original")
            output.unlink()
            target = root / "sensitive.txt"
            target.write_text("protected fixture")
            output.symlink_to(target)
            with self.assertRaises(FileExistsError):
                create_new_file(output, "not my file")
            self.assertEqual(target.read_text(), "protected fixture")

    def test_invalid_paths_and_controls_fail_closed(self):
        with self.assertRaises(ValueError):
            quote_exec_path("/bad\npath")
        with self.assertRaises(ValueError):
            quote_exec_path("")
        self.assertEqual(quote_exec_path("/path/a%20b"),
                         '"/path/a%%20b"')
        with tempfile.TemporaryDirectory(prefix="gc-tasks-invalid-") as directory:
            invalid = Path(directory)
            with self.assertRaises(ValueError):
                create_entry(invalid, Path(sys.executable))
            (invalid / "main.py").symlink_to(ROOT / "main.py")
            (invalid / "Main.qml").write_text("not executable")
            with self.assertRaises(ValueError):
                create_entry(invalid, Path(sys.executable))

    def test_generate_valid_desktop_file_only_in_disposable_directory(self):
        with tempfile.TemporaryDirectory(prefix="gc-tasks-xdg-entry-") as directory:
            output = Path(directory) / "tasks.desktop"
            self.assertEqual(main(["--output", str(output),
                                   "--linux-source", str(ROOT),
                                   "--python", sys.executable]), 0)
            self.assertTrue(output.is_file())
            self.assertTrue(output.stat().st_mode & 0o400)
            validator = shutil.which("desktop-file-validate")
            if validator:
                completed = subprocess.run([validator, str(output)],
                                           text=True, capture_output=True,
                                           timeout=10, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_generated_entry_escapes_special_paths(self):
        with tempfile.TemporaryDirectory(prefix="gc-tasks-ext-") as directory:
            source = Path(directory) / "a path with%spaces"
            source.mkdir()
            (source / "main.py").write_text("print('synthetic')\n")
            (source / "Main.qml").write_text("import QtQuick\n")
            content = create_entry(source, Path(sys.executable))
            self.assertIn("with%%spaces", content)
            validator = shutil.which("desktop-file-validate")
            if validator:
                output = Path(directory) / "special.desktop"
                create_new_file(output, content)
                completed = subprocess.run([validator, str(output)],
                                           text=True, capture_output=True,
                                           timeout=10, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
