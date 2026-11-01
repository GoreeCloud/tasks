"""Synthetic local-only persistence and conflict tests for OfflineOutbox."""
import sys
from concurrent.futures import ThreadPoolExecutor
import tempfile
from pathlib import Path
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from outbox import OfflineOutbox, OutboxError, StaleCursor


class OfflineOutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "outbox.sqlite3"
        self.store = OfflineOutbox(self.path)
        self.task_id = str(uuid4())
        self.mutation_id = str(uuid4())

    def tearDown(self):
        self.temp.cleanup()

    def change(self, seq=1, revision=1, *, deleted=False, title="Plan"):
        return {"seq": seq, "operation": "deleted" if deleted else "created" if revision == 1 else "updated",
                "task": {"id": self.task_id, "title": title, "priority": 2,
                         "revision": revision, "deleted": deleted}}

    def page(self, *changes, cursor=None, has_more=False):
        if cursor is None:
            cursor = changes[-1]["seq"] if changes else self.store.cursor()
        return {"changes": list(changes), "cursor": cursor, "hasMore": has_more}

    def test_restarts_retain_pending_payloads_without_reissuing_id(self):
        assert self.store.queue(self.mutation_id, self.task_id, "create", {"title": "Hello"})
        again = OfflineOutbox(self.path)
        self.assertEqual(again.pending()[0]["id"], self.mutation_id)
        self.assertEqual(again.pending()[0]["payload"], {"title": "Hello"})
        self.assertFalse(again.queue(self.mutation_id, self.task_id, "create", {"title": "Hello"}))
        self.assertEqual(len(again.pending()), 1)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_mutation_id_collision_and_wrong_input_are_rejected(self):
        self.store.queue(self.mutation_id, self.task_id, "create", {"title": "A"})
        cases = [(self.mutation_id, self.task_id, "create", {"title": "B"}),
                 ("broken", self.task_id, "create", {"title": "A"}),
                 (str(uuid4()), self.task_id, "delete", {"bad": True})]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(OutboxError):
                self.store.queue(*args)
        with self.assertRaises(OutboxError):
            self.store.queue(str(uuid4()), self.task_id, "update", {"title": "B"}, True)
        with self.assertRaises(OutboxError):
            self.store.queue(str(uuid4()), self.task_id, "create", {"title": "X" * 70000})
        with self.assertRaises(OutboxError):
            self.store.queue(str(uuid4()), self.task_id, "create", {"title": "\ud800"})
        self.assertEqual(len(self.store.pending()), 1)

    def test_concurrent_duplicate_enqueues_retain_one_mutation(self):
        def enqueue(_):
            return self.store.queue(
                self.mutation_id, self.task_id, "create", {"title": "One copy"}
            )

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(enqueue, range(6)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(OfflineOutbox(self.path).pending()), 1)

    def test_acknowledgement_is_idempotent_but_conflict_cannot_be_acked(self):
        self.store.queue(self.mutation_id, self.task_id, "create", {"title": "A"})
        self.assertTrue(self.store.acknowledge(self.mutation_id))
        self.assertFalse(self.store.acknowledge(self.mutation_id))
        self.assertEqual(self.store.pending(), [])
        with self.assertRaises(OutboxError):
            self.store.acknowledge(str(uuid4()))
        other = str(uuid4())
        self.store.queue(other, self.task_id, "update", {"title": "B"}, 1)
        self.store.mark_conflict(other, {"title": "Server version"})
        self.assertEqual(self.store.conflict(other)["title"], "Server version")
        with self.assertRaises(OutboxError):
            self.store.acknowledge(other)

    def test_change_page_commits_checkpoint_and_projection_atomically(self):
        self.assertEqual(self.store.cursor(), 0)
        first = self.change()
        self.assertEqual(self.store.apply_change_page(self.page(first), 0), 1)
        self.assertEqual(OfflineOutbox(self.path).cursor(), 1)
        self.assertEqual(self.store.remote_task(self.task_id)["title"], "Plan")
        second = self.change(seq=2, revision=2, title="Updated")
        self.assertEqual(self.store.apply_change_page(self.page(second), 1), 2)
        self.assertEqual(self.store.remote_task(self.task_id)["title"], "Updated")
        with self.assertRaises(StaleCursor):
            self.store.apply_change_page(self.page(second), 1)
        self.assertEqual(self.store.cursor(), 2)

    def test_corrupted_second_event_rolls_back_first_event(self):
        one = self.change()
        two = self.change(seq=2, revision=1, title="Invalid duplicate revision")
        with self.assertRaises(OutboxError):
            self.store.apply_change_page(self.page(one, two), 0)
        self.assertEqual(self.store.cursor(), 0)
        self.assertIsNone(self.store.remote_task(self.task_id))
        with self.assertRaises(OutboxError):
            self.store.apply_change_page(self.page(self.change(seq=2)), 0)
        self.assertEqual(self.store.cursor(), 0)

    def test_conflicts_retain_unsent_mutations_and_server_snapshot(self):
        self.store.queue(self.mutation_id, self.task_id, "update", {"title": "Offline edit"}, 1)
        first = self.change(seq=1, revision=2, title="Remote edit")
        self.store.apply_change_page(self.page(first), 0)
        self.assertEqual(self.store.pending(), [])
        self.assertEqual(self.store.conflict(self.mutation_id)["title"], "Remote edit")
        self.assertEqual(self.store.remote_task(self.task_id)["title"], "Remote edit")
        with self.assertRaises(OutboxError):
            self.store.acknowledge(self.mutation_id)

    def test_invalid_cursor_and_deleted_markers_are_rejected(self):
        for event in (self.change(seq=0),
                      {**self.change(), "operation": "deleted"},
                      {**self.change(), "task": {**self.change()["task"], "revision": True}}):
            with self.subTest(event=event), self.assertRaises(OutboxError):
                self.store.apply_change_page(self.page(event), 0)
        self.assertEqual(self.store.cursor(), 0)

    def test_seed_consistent_bootstrap_and_resume_changes(self):
        from api import TaskDatabase
        server = TaskDatabase(Path(self.temp.name) / "source.sqlite3")
        created = server.create_task(
            {"title": "Existing before first sync"}, "seed-bootstrap-test-0001"
        )
        deleted = server.create_task(
            {"title": "Already removed"}, "seed-bootstrap-test-0002"
        )
        server.delete_task(deleted["id"], 1)
        initial = server.bootstrap()
        self.assertEqual(initial["cursor"], 3)
        self.assertEqual(len(initial["tasks"]), 1)
        self.assertEqual(self.store.seed_bootstrap(initial), 3)
        self.assertEqual(self.store.remote_task(created["id"])["title"], "Existing before first sync")
        self.assertIsNone(self.store.remote_task(deleted["id"]))
        self.assertEqual(OfflineOutbox(self.path).cursor(), 3)
        with self.assertRaises(OutboxError):
            self.store.seed_bootstrap(initial)
        server.update_task(created["id"], {"title": "Newer title"}, 1)
        page = server.changes(after=3)
        self.assertEqual(self.store.apply_change_page(page, 3), 4)
        self.assertEqual(self.store.remote_task(created["id"])["title"], "Newer title")

    def test_refuse_incomplete_duplicate_or_dirty_bootstrap(self):
        task = self.change()["task"]
        original = {"schemaVersion": 1, "cursor": 1, "tasks": [task]}
        for data in (
            {"schemaVersion": 1, "cursor": 1},
            {"schemaVersion": 1, "cursor": -1, "tasks": [task]},
            {"schemaVersion": 1, "cursor": 1, "tasks": [task, task]},
            {"schemaVersion": 1, "cursor": 1, "tasks": [{**task, "deleted": True}]},
            {"schemaVersion": 2, "cursor": 1, "tasks": [task]},
        ):
            with self.subTest(data=data), self.assertRaises(OutboxError):
                self.store.seed_bootstrap(data)
            self.assertEqual(self.store.cursor(), 0)
        self.store.queue(self.mutation_id, self.task_id, "create", {"title": "Local draft"})
        with self.assertRaises(OutboxError):
            self.store.seed_bootstrap(original)
        self.assertEqual(len(self.store.pending()), 1)

    def test_empty_bootstrap_can_only_be_applied_once(self):
        empty = {"schemaVersion": 1, "cursor": 0, "tasks": []}
        self.assertEqual(self.store.seed_bootstrap(empty), 0)
        with self.assertRaises(OutboxError):
            OfflineOutbox(self.path).seed_bootstrap(empty)

    def test_existing_loopback_api_change_feed_contract_offline(self):
        # Exercise the existing server's real persisted change shape, with no
        # HTTP access, credentials, external network, or production data.
        from api import TaskDatabase
        server = TaskDatabase(Path(self.temp.name) / "server.sqlite3")
        created = server.create_task(
            {"title": "Real change feed", "priority": 1}, "outbox-contract-key-0001"
        )
        expected_id = created["id"]
        first_page = server.changes(after=0, limit=1)
        self.assertEqual(self.store.apply_change_page(first_page, 0), 1)
        self.assertEqual(self.store.remote_task(expected_id)["title"], "Real change feed")

        pending = str(uuid4())
        self.store.queue(pending, expected_id, "update", {"title": "Offline edit"}, 1)
        server.update_task(expected_id, {"title": "Server edit"}, 1)
        server.delete_task(expected_id, 2)
        second_page = server.changes(after=1, limit=2)
        self.assertEqual(self.store.apply_change_page(second_page, 1), 3)
        self.assertEqual(self.store.cursor(), 3)
        self.assertTrue(self.store.remote_task(expected_id)["deleted"])
        self.assertEqual(self.store.conflict(pending)["title"], "Server edit")
        self.assertEqual(self.store.pending(), [])
        self.assertEqual(OfflineOutbox(self.path).cursor(), 3)

    def test_event_origin_mismatch_and_invalid_identifier_roll_back(self):
        self.store.queue(self.mutation_id, self.task_id, "delete", {}, 1)
        mismatched = {**self.change(), "mutationId": self.mutation_id}
        with self.assertRaises(OutboxError):
            self.store.apply_change_page(self.page(mismatched), 0)
        self.assertEqual(self.store.cursor(), 0)
        self.assertIsNone(self.store.remote_task(self.task_id))
        self.assertEqual(self.store.pending()[0]["id"], self.mutation_id)

        invalid = {**self.change(), "mutationId": "bad key"}
        with self.assertRaises(OutboxError):
            self.store.apply_change_page(self.page(invalid), 0)
        self.assertEqual(self.store.cursor(), 0)

    def test_symlinked_database_is_rejected(self):
        alias = Path(self.temp.name) / "alias.sqlite3"
        alias.symlink_to(self.path)
        with self.assertRaises(OutboxError):
            OfflineOutbox(alias)


if __name__ == "__main__":
    unittest.main()
