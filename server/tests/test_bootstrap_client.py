"""Transport-injected Tasks bootstrap tests. Only disposable SQLite, no network."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import ApiError, TaskDatabase
from bootstrap_client import SnapshotChanged, collect_and_seed
from outbox import OfflineOutbox, OutboxError, StaleCursor


class BootstrapCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = TaskDatabase(self.root / "source.sqlite3")
        self.outbox = OfflineOutbox(self.root / "receiver.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def seed_source(self, count):
        return [
            self.source.create_task({"title": "Synthetic %03d" % i},
                                    "collector-seed-%05d" % i)
            for i in range(count)
        ]

    def fetch(self, *, limit, after, checkpoint):
        try:
            return self.source.bootstrap_page(limit, after=after, checkpoint=checkpoint)
        except ApiError as exc:
            if exc.status == 409:
                raise SnapshotChanged() from None
            raise

    def test_complete_103_item_snapshot_then_delta_after_checkpoint(self):
        tasks = self.seed_source(103)
        observed = []

        def callback(**params):
            observed.append(dict(params))
            return self.fetch(**params)

        self.assertEqual(collect_and_seed(self.outbox, callback, limit=23), 103)
        self.assertEqual([p["after"] for p in observed[:1]], [None])
        self.assertEqual(len(observed), 5)
        self.assertEqual([p["checkpoint"] for p in observed], [None, 103, 103, 103, 103])
        self.assertEqual(self.outbox.cursor(), 103)
        self.assertTrue(all(self.outbox.remote_task(item["id"]) == item for item in tasks))
        changed = self.source.update_task(tasks[0]["id"], {"title": "Revised"}, 1)
        page = self.source.changes(after=103)
        self.assertEqual(self.outbox.apply_change_page(page, 103), 104)
        self.assertEqual(self.outbox.remote_task(tasks[0]["id"])["title"], changed["title"])
        with self.assertRaises(OutboxError):
            collect_and_seed(self.outbox, callback)

    def test_churn_restarts_with_fresh_checkpoint_and_never_seeds_partial(self):
        tasks = self.seed_source(3)
        calls = []
        changed = False

        def callback(**params):
            nonlocal changed
            calls.append(dict(params))
            if params["after"] is not None and not changed:
                changed = True
                self.source.update_task(tasks[0]["id"], {"title": "Concurrent edit"}, 1)
            return self.fetch(**params)

        self.assertEqual(collect_and_seed(self.outbox, callback, limit=2), 4)
        self.assertEqual([p["checkpoint"] for p in calls], [None, 3, None, 4])
        self.assertEqual(self.outbox.cursor(), 4)
        self.assertEqual(self.outbox.remote_task(tasks[0]["id"])["title"], "Concurrent edit")

    def test_repeated_churn_exhausts_budget_without_writing(self):
        self.seed_source(3)
        failures = 0

        def callback(**params):
            nonlocal failures
            if params["after"] is not None:
                failures += 1
                raise SnapshotChanged()
            return self.fetch(**params)

        with self.assertRaises(StaleCursor):
            collect_and_seed(self.outbox, callback, limit=2, max_restarts=2)
        self.assertEqual(failures, 3)
        self.assertEqual(self.outbox.cursor(), 0)
        self.assertIsNone(self.outbox.remote_task(next(iter(
            self.source.list_tasks()))["id"]))

    def test_invalid_or_untrusted_page_denied_without_retry(self):
        self.seed_source(2)
        good = self.fetch(limit=2, after=None, checkpoint=None)
        cases = [
            {**good, "limit": 100},
            {**good, "unexpectedMeta": "private"},
            {**good, "tasks": [{**good["tasks"][0], "extra": "private"}] +
                              good["tasks"][1:]},
            {**good, "checkpoint": True},
            {**good, "schemaVersion": 3},
            {**good, "tasks": good["tasks"][::-1]},
            {**good, "tasks": good["tasks"] * 2},
            {**good, "hasMore": True, "nextAfter": None},
            {**good, "hasMore": True, "nextAfter": "invalid"},
            {**good, "hasMore": False, "nextAfter": good["tasks"][-1]["id"]},
            {**good, "tasks": [{**good["tasks"][0], "id": "not-uuid"}]},
        ]
        for corrupt in cases:
            attempts = []
            def callback(**params):
                attempts.append(params)
                return corrupt
            with self.subTest(corrupt=corrupt), self.assertRaises(OutboxError):
                collect_and_seed(self.outbox, callback, limit=2)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(self.outbox.cursor(), 0)

    def test_empty_snapshot_is_accepted_once(self):
        self.assertEqual(collect_and_seed(self.outbox, self.fetch), 0)
        self.assertEqual(self.outbox.cursor(), 0)
        with self.assertRaises(OutboxError):
            collect_and_seed(self.outbox, self.fetch)

    def test_rejects_bad_budgets_and_preserves_local_edits(self):
        for kwargs in [
            {"limit": 0}, {"limit": 101}, {"limit": True},
            {"max_restarts": -1}, {"max_restarts": 4},
            {"max_restarts": False},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(OutboxError):
                collect_and_seed(self.outbox, self.fetch, **kwargs)
        self.seed_source(1)
        from uuid import uuid4
        self.outbox.queue(str(uuid4()), str(uuid4()), "create", {"title": "Local draft"})
        with self.assertRaises(OutboxError):
            collect_and_seed(self.outbox, self.fetch)
        self.assertEqual(len(self.outbox.pending()), 1)
        self.assertEqual(self.outbox.cursor(), 0)


if __name__ == "__main__":
    unittest.main()
