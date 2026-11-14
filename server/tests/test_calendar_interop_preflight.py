"""Synthetic, non-mutating Tasks-to-Calendar preflight regression tests."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from outbox import OutboxError
from calendar_interop_preflight import calendar_import_preflight

class CalendarVtodoPreflightTests(unittest.TestCase):
    def setUp(self):
        self.task = {
            "id": "93cded7e-431f-4a8d-ae95-47be27d7b4a4",
            "title": "SECRET_SOURCE_TITLE_NEVER_EMIT",
            "due": None, "priority": 3, "completed": False, "revision": 1,
            "updatedAt": "2026-11-11T12:00:00Z", "deleted": False,
            "privateProviderNote": "SECRET_PROVIDER_DATA_NEVER_EMIT",
        }

    def check(self, **changed):
        task = {**self.task, **changed}
        original = copy.deepcopy(task)
        result = calendar_import_preflight(task)
        self.assertEqual(task, original)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["source_profile"], "tasks.vtodo-preview.v1")
        self.assertEqual(result["target_profile"], "calendar.vtodo-draft.20261111")
        self.assertFalse(result["mutates_data"])
        self.assertTrue(result["requires_user_consent"])
        self.assertFalse(result["full_fidelity_verified"])
        encoded = json.dumps(result)
        for forbidden in (task["id"], task["title"], task["privateProviderNote"]):
            self.assertNotIn(forbidden, encoded)
        return result["reason_codes"]

    def test_undated_task_fails_for_revision_privacy_and_timestamp_loss(self):
        self.assertEqual(self.check(), [
            "revision_not_supported", "privacy_class_not_supported",
            "update_timestamp_not_preserved",
        ])

    def test_date_only_due_is_explicitly_not_reinterpreted_as_midnight(self):
        self.assertIn("date_only_due_not_supported", self.check(due="2026-11-12"))
        self.assertNotIn("date_only_due_not_supported", self.check())

    def test_nondefault_priority_is_reported_before_silent_downgrade(self):
        for priority in (1, 2, 4):
            with self.subTest(priority=priority):
                self.assertIn("priority_not_exported", self.check(priority=priority))

    def test_invalid_or_absent_priority_is_unproven_not_implicitly_p3(self):
        for priority in (None, True, "3", 0, 5):
            with self.subTest(priority=repr(priority)):
                self.assertIn("priority_not_proven", self.check(priority=priority))

    def test_calendar_title_length_ceiling_is_reported(self):
        self.assertIn("title_too_long_for_calendar", self.check(title="G" * 170))
        self.assertNotIn("title_too_long_for_calendar", self.check(title="G" * 160))

    def test_invalid_or_deleted_source_cannot_produce_compatibility_report(self):
        for changed in ({"deleted": True}, {"due": "2026-02-30"},
                        {"revision": 0}, {"title": "not safe\u202E"}):
            with self.subTest(changed=changed), self.assertRaises(OutboxError):
                calendar_import_preflight({**self.task, **changed})
        with self.assertRaises(OutboxError):
            calendar_import_preflight(dict)
