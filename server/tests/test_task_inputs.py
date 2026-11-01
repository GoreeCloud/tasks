"""Unit tests for the task input validation contract."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import normalize_task_fields

class TaskInputTests(unittest.TestCase):
    def test_accepts_unicode_titles(self):
        task = normalize_task_fields({"title": "  café  "}, create=True)
        self.assertEqual(task["title"], "café")
        self.assertEqual(task["priority"], 4)

if __name__ == "__main__":
    unittest.main()
