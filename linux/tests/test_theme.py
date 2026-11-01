import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme import (
    ACCENTS, APPEARANCES, normalize, read_preferences, semantic_css, write_preferences
)


class ThemePreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "prefs" / "appearance.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_light_and_neutral_is_default_even_without_os_theme(self):
        self.assertEqual(read_preferences(self.path),
                         {"appearance": "light", "accent": "neutral"})
        self.assertEqual(normalize("invalid", "violet"),
                         {"appearance": "light", "accent": "neutral"})
        self.assertIn("background-color: #374151", semantic_css("light", "neutral"))
        self.assertIn("color: #ffffff", semantic_css("light", "neutral"))

    def test_all_semantic_pairs_and_preference_persistence(self):
        for appearance in APPEARANCES:
            for accent in ACCENTS:
                write_preferences(appearance, accent, self.path)
                self.assertEqual(read_preferences(self.path),
                                 {"appearance": appearance, "accent": accent})
                self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
                css = semantic_css(appearance, accent)
                self.assertIn("button.suggested-action", css)
                self.assertNotIn("undefined", css)

    def test_bad_data_cannot_disable_light_default_or_escape_to_tasks(self):
        self.path.parent.mkdir(parents=True)
        for raw in ('not-json', '{"appearance":"auto","accent":"purple"}',
                    '[]', '{"appearance":true}', 'X' * 4097):
            self.path.write_text(raw)
            self.assertEqual(read_preferences(self.path),
                             {"appearance": "light", "accent": "neutral"})
        for appearance, accent in (("auto", "neutral"), ("light", "purple"),
                                   (None, None)):
            with self.assertRaises(ValueError):
                write_preferences(appearance, accent, self.path)

    def test_preferences_refuse_symlink_and_do_not_overwrite_other_files(self):
        target = Path(self.temp.name) / "unrelated.json"
        target.write_text('important')
        self.path.parent.mkdir(parents=True)
        self.path.symlink_to(target)
        self.assertEqual(read_preferences(self.path), normalize())
        with self.assertRaises(ValueError):
            write_preferences("dark", "lagoon", self.path)
        self.assertEqual(target.read_text(), "important")


if __name__ == "__main__":
    unittest.main()
