"""Synthetic SQLite tests for retry receipts; no real credentials or network."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retry_receipts import fingerprint, MutationReceipts, ReceiptError, ReceiptConflict


class RetryReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "dev.sqlite3"
        self.task_id = str(uuid4())
        self.key = "retry-mutation-0001"
        with self.db() as db:
            db.execute("""CREATE TABLE idempotency(
                request_key TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,
                response_json TEXT NOT NULL)""")
            db.execute("CREATE TABLE changes(seq INTEGER PRIMARY KEY, op TEXT)")

    def tearDown(self):
        self.tmp.cleanup()

    def db(self):
        return sqlite3.connect(self.path, timeout=10)

    def mutate(self, key=None, *, value="new", revision=1):
        key = key or self.key
        digest = fingerprint("PATCH", self.task_id, revision, {"title": value})
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            reply = MutationReceipts.lookup(db, key, digest)
            if reply is not None:
                return reply
            db.execute("INSERT INTO changes(op) VALUES (?)", (value,))
            reply = {"id": self.task_id, "revision": revision + 1, "title": value}
            MutationReceipts.save(db, key, digest, reply)
            return reply

    def test_retry_does_not_append_second_event(self):
        first = self.mutate()
        self.assertEqual(self.mutate(), first)
        with self.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM changes").fetchone()[0], 1)

    def test_receipt_survives_database_reopen(self):
        result = self.mutate()
        with self.db() as db:
            digest = fingerprint("PATCH", self.task_id, 1, {"title": "new"})
            self.assertEqual(MutationReceipts.lookup(db, self.key, digest), result)

    def test_changed_payload_conflicts(self):
        self.mutate()
        with self.assertRaises(ReceiptConflict):
            self.mutate(value="different")

    def test_changed_revision_conflicts(self):
        self.mutate()
        with self.assertRaises(ReceiptConflict):
            self.mutate(revision=2)

    def test_cross_method_task_and_precondition_are_distinct(self):
        same = fingerprint("PATCH", self.task_id, 1, {"title": "new"})
        self.assertNotEqual(same, fingerprint("DELETE", self.task_id, 1, None))
        self.assertNotEqual(same, fingerprint("PATCH", str(uuid4()), 1, {"title": "new"}))
        self.assertNotEqual(same, fingerprint("PATCH", self.task_id, 2, {"title": "new"}))

    def test_rejects_malformed_keys_and_inputs(self):
        for key in ("short", "unsafe space", "x" * 129, "💥"):
            with self.subTest(key=key), self.assertRaises(ReceiptError):
                with self.db() as db:
                    MutationReceipts.lookup(db, key, "a" * 64)
        for method, id_, revision, fields in (
            ("POST", self.task_id, 1, {}),
            ("PATCH", "not-uuid", 1, {"title": "ok"}),
            ("PATCH", self.task_id, True, {"title": "ok"}),
            ("PATCH", self.task_id, 1, {"title": "\ud800"}),
            ("DELETE", self.task_id, 1, {"title": "unexpected"}),
        ):
            with self.assertRaises(ReceiptError):
                fingerprint(method, id_, revision, fields)

    def test_atomic_rollback_excludes_receipt_and_event(self):
        digest = fingerprint("PATCH", self.task_id, 1, {"title": "bad"})
        try:
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("INSERT INTO changes(op) VALUES ('bad')")
                MutationReceipts.save(db, "atomic-retry-0001", digest, {"title": "bad"})
                raise RuntimeError("simulated crash")
        except RuntimeError:
            pass
        with self.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM changes").fetchone()[0], 0)
            self.assertIsNone(MutationReceipts.lookup(db, "atomic-retry-0001", digest))

    def test_concurrent_identical_mutations_append_once(self):
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: self.mutate(), range(6)))
        self.assertEqual(len({result["revision"] for result in results}), 1)
        with self.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM changes").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
