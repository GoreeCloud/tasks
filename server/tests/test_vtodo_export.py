"""Pure, synthetic VTODO RFC 5545 preview tests. No networking or data files."""
import sys
from pathlib import Path
from uuid import uuid4
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from outbox import OutboxError
from vtodo_export import vtodo_preview


class VtodoPreviewTests(unittest.TestCase):
    def setUp(self):
        self.uid = str(uuid4())
        self.task = {
            "id": self.uid, "title": "Plan a launch", "priority": 3,
            "due": "2026-11-12", "completed": False, "revision": 1,
            "updatedAt": "2026-11-10T22:43:10.123Z",
            "deleted": False,
            "privateProviderNote": "do-not-export-999",
        }

    def render(self, **fields):
        return vtodo_preview({**self.task, **fields})

    def test_dav_rfc5545_shape_private_scope_stable_uid(self):
        raw = self.render()
        text = raw.decode("utf-8")
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"))
        self.assertTrue(text.endswith("END:VTODO\r\nEND:VCALENDAR\r\n"))
        for line in (
            "BEGIN:VTODO", "UID:urn:uuid:" + self.uid,
            "DTSTAMP:20261110T224310Z", "SEQUENCE:0", "CLASS:PRIVATE",
            "STATUS:NEEDS-ACTION", "SUMMARY:Plan a launch",
            "DUE;VALUE=DATE:20261112",
        ):
            self.assertIn(line + "\r\n", text)
        self.assertNotIn("do-not-export-999", text)
        self.assertEqual(raw, self.render())
        changed = self.render(revision=2, completed=True, title="Completed")
        self.assertIn(b"SEQUENCE:1\r\nCLASS:PRIVATE\r\nSTATUS:COMPLETED", changed)
        self.assertIn(("UID:urn:uuid:" + self.uid).encode("ascii"), changed)

    def test_escaped_text_cannot_inject_extra_calendar_components(self):
        title = "Team, Plan; Scope\\ Review\nBEGIN:VTODO\nEND:VCALENDAR"
        text = self.render(title=title).decode("utf-8")
        self.assertIn("SUMMARY:Team\\, Plan\\; Scope\\\\ Review\\nBEGIN:VTODO\\nEND:VCALENDAR", text)
        self.assertEqual(text.count("\r\nBEGIN:VTODO\r\n"), 1)
        self.assertEqual(text.count("\r\nEND:VCALENDAR\r\n"), 1)

    def test_utf8_folding_preserves_complete_codepoints(self):
        title = "会社🙂Renée" * 20
        text = self.render(title=title).decode("utf-8")
        lines = [line for line in text.split("\r\n") if line]
        self.assertTrue(all(len(line.encode("utf-8")) <= 75 for line in lines))
        self.assertTrue(any(line.startswith(" ") for line in lines))
        self.assertIn("SUMMARY:" + title, text.replace("\r\n ", ""))

    def test_no_due_date_has_no_inferred_midnight(self):
        text = self.render(due=None).decode("utf-8")
        self.assertNotIn("DUE:", text)
        self.assertIn("STATUS:NEEDS-ACTION", text)

    def test_rejects_invalid_or_deleted_task_without_partial_payload(self):
        invalid = [
            {"id": "invalid"}, {"id": self.uid.upper()},
            {"deleted": True}, {"deleted": None},
            {"completed": 1}, {"revision": 0}, {"revision": True},
            {"revision": 2147483648}, {"due": "2026-02-30"},
            {"due": "2026/11/12"}, {"updatedAt": "2026-11-10T21:43:10-01:00"},
            {"updatedAt": "2026-99-99T22:43:10Z"},
            {"title": ""}, {"title": "x" * 241},
            {"title": "bad\0value"}, {"title": "bad\u202Eflip"},
            {"title": "bad\u2066hide"}, {"title": "bad\u2028break"}, {"title": "bad\u0085break"},
            {"title": "bad\ud800surrogate"},
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(OutboxError):
                self.render(**values)


if __name__ == "__main__":
    unittest.main()
