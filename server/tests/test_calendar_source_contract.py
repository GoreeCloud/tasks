"""Source-owned Tasks serializer exercised against pinned genuine Calendar parser.

When GC_CALENDAR_SOURCE_DIR is unset these tests skip in ordinary unit suites.
Hosted source-contract CI MUST set that variable and verify the source commit
and blob SHA before invoking this module. No network, files or user data.
"""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vtodo_export import vtodo_preview
from calendar_interop_preflight import calendar_import_preflight

@unittest.skipUnless(os.environ.get("GC_CALENDAR_SOURCE_DIR"), "Pinned Calendar source not checked out")
class PinnedCalendarParserContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(os.environ["GC_CALENDAR_SOURCE_DIR"]).resolve()
        if not (source / "calendar_app/vtodo.py").is_file():
            raise AssertionError("Missing pinned Calendar parser")
        sys.path.insert(0, str(source))
        from calendar_app.vtodo import parse_tasks
        from calendar_app.ical import ImportErrorCalendar
        cls.parse_tasks = staticmethod(parse_tasks)
        cls.ImportErrorCalendar = ImportErrorCalendar

    @staticmethod
    def task(due=None, title="Synthetic task"):
        return {
            "id": "93cded7e-431f-4a8d-ae95-47be27d7b4a4",
            "title": title, "due": due, "priority": 3,
            "completed": False, "revision": 1,
            "updatedAt": "2026-11-11T12:00:00Z", "deleted": False,
        }

    def test_real_export_is_rejected_because_calendar_does_not_support_sequence(self):
        for due in (None, "2026-11-12"):
            with self.subTest(due=due):
                task = self.task(due=due)
                content = vtodo_preview(task).decode("utf-8")
                with self.assertRaisesRegex(self.ImportErrorCalendar, "SEQUENCE"):
                    self.parse_tasks(content)
                reasons = calendar_import_preflight(task)["reason_codes"]
                self.assertIn("revision_not_supported", reasons)
                self.assertIn("privacy_class_not_supported", reasons)

    def test_removed_metadata_diagnostic_is_not_an_authorized_conversion(self):
        for due in (None, "2026-11-12"):
            with self.subTest(due=due):
                content = vtodo_preview(self.task(due=due)).decode("utf-8")
                changed = "\r\n".join(line for line in content.split("\r\n")
                                     if not line.startswith(("SEQUENCE:", "CLASS:")))
                if due is None:
                    # Parser acceptance is deliberately NOT called lossless:
                    # privacy and source revisions have been discarded.
                    self.assertEqual(len(self.parse_tasks(changed)), 1)
                else:
                    with self.assertRaisesRegex(self.ImportErrorCalendar, "All-day VTODO"):
                        self.parse_tasks(changed)

    def test_overlong_title_cannot_be_silently_transferred(self):
        task = self.task(title="A" * 170)
        self.assertIn("title_too_long_for_calendar",
                      calendar_import_preflight(task)["reason_codes"])
