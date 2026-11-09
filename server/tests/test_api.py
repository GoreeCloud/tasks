"""No external network, credentials or real user data are used by API tests."""
import json
import sqlite3
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import TaskDatabase, make_handler
from outbox import OfflineOutbox

TOKEN = "synthetic-test-token-0123456789abcdef0123456789abcdef"


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "tasks.sqlite3"
        self.store = TaskDatabase(self.path)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, TOKEN))
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def request(self, method, path, body=None, *, auth=True, headers=None):
        options = headers.copy() if headers else {}
        if auth:
            options["Authorization"] = "Bearer " + TOKEN
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            options["Content-Type"] = "application/json"
        req = Request(self.origin + path, data=data, method=method, headers=options)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            result = json.loads(response.read())
            cache_control = response.headers.get("Cache-Control")
        return status, result, cache_control

    def create(self, title="One", key="unique-create-0001", **fields):
        return self.request(
            "POST", "/v1/tasks", {"title": title, **fields},
            headers={"Idempotency-Key": key}
        )

    def test_health_and_authorization(self):
        self.assertEqual(self.request("GET", "/healthz", auth=False)[0], 200)
        self.assertEqual(self.request("GET", "/v1/tasks", auth=False)[0], 401)
        self.assertEqual(self.request("GET", "/v1/changes", auth=False)[0], 401)
        status, response, cache = self.request("GET", "/v1/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(cache, "no-store")
        self.assertEqual(response["tasks"], [])

    def test_abusive_headers_and_large_parameters_fail_closed(self):
        status, _, _ = self.request("GET", "/v1/tasks", auth=False, headers={"Authorization": "Bearer ñ"})
        self.assertEqual(status, 401)
        self.assertEqual(self.request("GET", "/v1/tasks?limit=" + "9" * 1000)[0], 400)
        self.assertEqual(self.request("GET", "/v1/changes?after=" + "9" * 1000)[0], 400)
        task = self.create("Protected")[1]
        self.assertEqual(self.request("PATCH", "/v1/tasks/" + task["id"], {"title": "Unsafe"},
                                      headers={"If-Match": "9" * 1000})[0], 428)

    def test_authenticated_bootstrap_snapshot_and_delta_checkpoint(self):
        self.assertEqual(self.request("GET", "/v1/bootstrap", auth=False)[0], 401)
        empty = self.request("GET", "/v1/bootstrap")[1]
        self.assertEqual(empty, {"schemaVersion": 1, "tasks": [], "cursor": 0})
        self.assertEqual(self.request("GET", "/v1/bootstrap?limit=5")[0], 400)
        created = self.create("Before checkpoint", key="bootstrap-key-0001")[1]
        snapshot = self.request("GET", "/v1/bootstrap")[1]
        self.assertEqual(snapshot["schemaVersion"], 1)
        self.assertEqual(snapshot["cursor"], 1)
        self.assertEqual([task["id"] for task in snapshot["tasks"]], [created["id"]])
        self.create("After checkpoint", key="bootstrap-key-0002")
        feed = self.request("GET", "/v1/changes?after=" + str(snapshot["cursor"]))[1]
        self.assertEqual([item["seq"] for item in feed["changes"]], [2])
        self.assertEqual(feed["cursor"], 2)

    def test_bootstrap_refuses_to_silently_truncate_workspace(self):
        for index in range(101):
            status, _, _ = self.create("task", key="bootstrap-limit-%04d" % index)
            self.assertEqual(status, 201)
        status, response, _ = self.request("GET", "/v1/bootstrap")
        self.assertEqual(status, 413)
        self.assertIn("100 tasks", response["error"].lower())

    def test_created_tasks_idempotency_and_conflicting_key(self):
        status, first, _ = self.create("Launch", priority=1, due="2026-11-07")
        self.assertEqual(status, 201)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["due"], "2026-11-07")
        self.assertEqual(self.create("Launch", priority=1, due="2026-11-07")[1], first)
        self.assertEqual(self.create("Different")[0], 409)
        self.assertEqual(len(self.request("GET", "/v1/tasks")[1]["tasks"]), 1)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 1)

    def test_non_destructive_change_schema_migration(self):
        import sqlite3
        dbpath = Path(self.tmp.name) / "legacy.sqlite3"
        with sqlite3.connect(dbpath) as db:
            db.execute("CREATE TABLE changes(seq INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,operation TEXT NOT NULL,snapshot_json TEXT NOT NULL)")
            db.execute("INSERT INTO changes(task_id,operation,snapshot_json) VALUES (?,?,?)", (str(uuid4()), "created", json.dumps({"title":"legacy"})))
        store = TaskDatabase(dbpath)
        self.assertEqual(store.changes()["changes"][0]["task"]["title"], "legacy")
        self.assertIsNone(store.changes()["changes"][0]["mutationId"])
        store.create_task({"title":"new"}, "migrate-test-0001")
        self.assertEqual(store.changes(after=1)["changes"][0]["mutationId"], "migrate-test-0001")
        self.assertEqual(TaskDatabase(dbpath).changes()["cursor"], 2)

    def test_offline_outbox_receipt_acknowledgement_and_delta_contract(self):
        """Synthetic loopback contract only: clients do not use the service."""
        created = self.create("Initial", key="integrated-create-0001")[1]
        path = "/v1/tasks/" + created["id"]
        offline = OfflineOutbox(Path(self.tmp.name) / "synthetic-outbox.sqlite3")
        bootstrap = self.request("GET", "/v1/bootstrap")[1]
        self.assertEqual(offline.seed_bootstrap(bootstrap), 1)

        update_id = str(uuid4())
        offline.queue(update_id, created["id"], "update", {"title": "Edited offline"}, 1)
        pending = offline.pending()
        self.assertEqual(len(pending), 1)
        headers = {"Idempotency-Key": pending[0]["id"],
                   "If-Match": str(pending[0]["expectedRevision"])}
        status, first, _ = self.request("PATCH", path, pending[0]["payload"], headers=headers)
        self.assertEqual(status, 200)
        # The first response is treated as lost; repeat the persisted ID.
        self.assertEqual(self.request("PATCH", path, pending[0]["payload"], headers=headers)[1], first)
        page = self.request("GET", "/v1/changes?after=1")[1]
        self.assertEqual(page["changes"][0]["mutationId"], update_id)
        # Simulate a pull arriving before the lost acknowledgement.
        self.assertEqual(offline.apply_change_page(page, 1), 2)
        self.assertFalse(offline.acknowledge(update_id))
        self.assertEqual(offline.remote_task(created["id"])["title"], "Edited offline")
        self.assertIsNone(offline.conflict(update_id))

        delete_id = str(uuid4())
        offline.queue(delete_id, created["id"], "delete", {}, 2)
        pending = offline.pending()
        self.assertEqual(len(pending), 1)
        headers = {"Idempotency-Key": pending[0]["id"],
                   "If-Match": str(pending[0]["expectedRevision"])}
        status, tombstone, _ = self.request("DELETE", path, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(self.request("DELETE", path, headers=headers)[1], tombstone)
        page = self.request("GET", "/v1/changes?after=2")[1]
        self.assertEqual(page["changes"][0]["mutationId"], delete_id)
        self.assertEqual(offline.apply_change_page(page, 2), 3)
        self.assertFalse(offline.acknowledge(delete_id))
        self.assertIsNone(offline.conflict(delete_id))
        self.assertTrue(offline.remote_task(created["id"])["deleted"])
        self.assertEqual(offline.pending(), [])
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 3)

    def test_retry_receipts_patch_delete_and_duplicate_changes(self):
        created = self.create("Work", key="receipt-create-0001")[1]
        path = "/v1/tasks/" + created["id"]
        patch_headers = {"If-Match": "1", "Idempotency-Key": "receipt-patch-0001"}
        status, updated, _ = self.request("PATCH", path, {"title": "Updated"}, headers=patch_headers)
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(self.request("PATCH", path, {"title": "Updated"}, headers=patch_headers)[1], updated)
        self.assertEqual(self.request("PATCH", path, {"title": "Changed"}, headers=patch_headers)[0], 409)
        self.assertEqual(self.request("PATCH", path, {"title": "Updated"},
                                      headers={"If-Match": "2", "Idempotency-Key": "receipt-patch-0001"})[0], 409)
        self.assertEqual(self.request("PATCH", path, {"title": "Updated"},
                                      headers={"If-Match": "1", "Idempotency-Key": "receipt-patch-0002"})[0], 409)
        self.assertEqual(self.request("PATCH", path, {"title": "Updated"},
                                      headers={"If-Match": "2", "Idempotency-Key": "receipt-create-0001"})[0], 409)
        self.assertEqual(self.request("PATCH", path, {"title": "Updated"},
                                      headers={"If-Match": "2", "Idempotency-Key": "bad key"})[0], 400)

        delete_headers = {"If-Match": "2", "Idempotency-Key": "receipt-delete-0001"}
        status, deleted, _ = self.request("DELETE", path, headers=delete_headers)
        self.assertEqual(status, 200)
        self.assertTrue(deleted["deleted"])
        self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("DELETE", path, headers=delete_headers)[1], deleted)
        self.assertEqual(self.request("DELETE", path, headers={"If-Match": "1",
                              "Idempotency-Key": "receipt-delete-0001"})[0], 409)
        self.assertEqual(self.request("DELETE", path, headers={"If-Match": "2",
                              "Idempotency-Key": "receipt-delete-0002"})[0], 404)
        self.assertEqual(self.request("PATCH", path, {"title": "Updated"},
                              headers={"If-Match": "2", "Idempotency-Key": "receipt-delete-0001"})[0], 409)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 3)
        self.assertEqual(TaskDatabase(self.path).delete_task(created["id"], 2,
                             key="receipt-delete-0001"), deleted)

    def test_concurrent_patch_retries_append_one_event(self):
        created = self.create("Before", key="concurrent-create-0001")[1]
        path = "/v1/tasks/" + created["id"]
        headers = {"If-Match": "1", "Idempotency-Key": "concurrent-patch-0001"}
        def replay(_):
            return self.request("PATCH", path, {"title": "After"}, headers=headers)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(replay, range(6)))
        self.assertTrue(all(status == 200 for status, _, _ in results))
        self.assertTrue(all(payload == results[0][1] for _, payload, _ in results))
        self.assertEqual(self.request("GET", path)[1]["revision"], 2)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 2)

    def test_failed_transaction_does_not_persist_receipt(self):
        created = self.create("Before", key="rollback-create-0001")[1]
        original = self.store._record_change
        def fail(*_args):
            raise RuntimeError("synthetic rollback")
        self.store._record_change = fail
        try:
            with self.assertRaises(RuntimeError):
                self.store.update_task(created["id"], {"title": "After"}, 1,
                                       key="rollback-patch-0001")
        finally:
            self.store._record_change = original
        self.assertEqual(self.store.get_task(created["id"])["revision"], 1)
        updated = self.store.update_task(created["id"], {"title": "After"}, 1,
                                         key="rollback-patch-0001")
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(len(self.store.changes()["changes"]), 2)

    def test_optimistic_revisions_and_historical_change_snapshots(self):
        _, created, _ = self.create("Draft")
        task_id = created["id"]
        path = "/v1/tasks/" + task_id
        self.assertEqual(self.request("PATCH", path, {"title": "Rewritten"})[0], 428)
        self.assertEqual(self.request("PATCH", path, {"title": "Rewritten"}, headers={"If-Match": "2"})[0], 409)
        status, changed, _ = self.request(
            "PATCH", path, {"title": "Rewritten", "completed": True},
            headers={"If-Match": "1"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(changed["revision"], 2)
        self.assertTrue(changed["completed"])
        self.assertEqual(self.request("DELETE", path, headers={"If-Match": "1"})[0], 409)
        self.assertEqual(self.request("DELETE", path, headers={"If-Match": "2"})[0], 200)
        self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.request("GET", "/v1/tasks")[1]["tasks"], [])
        feed = self.request("GET", "/v1/changes?after=0&limit=2")[1]
        self.assertTrue(feed["hasMore"])
        self.assertEqual([e["operation"] for e in feed["changes"]], ["created", "updated"])
        self.assertEqual(feed["changes"][0]["task"]["title"], "Draft")
        self.assertEqual(feed["changes"][1]["task"]["title"], "Rewritten")
        remaining = self.request("GET", "/v1/changes?after=" + str(feed["cursor"]))[1]
        self.assertEqual(len(remaining["changes"]), 1)
        self.assertEqual(remaining["changes"][0]["operation"], "deleted")
        self.assertTrue(remaining["changes"][0]["task"]["deleted"])

    def test_malformed_input_does_not_modify_database(self):
        self.assertEqual(self.create("Bad date", due="2026-02-30")[0], 422)
        self.assertEqual(self.create("Bad priority", priority=True)[0], 422)
        self.assertEqual(self.create("", priority=1)[0], 422)
        self.assertEqual(self.create("Unknown", unexpected="field")[0], 422)
        self.assertEqual(self.request(
            "POST", "/v1/tasks", {"title": "Missing key"}
        )[0], 400)
        self.assertEqual(self.request("GET", "/v1/tasks?limit=999")[0], 400)
        self.assertEqual(self.request("GET", "/v1/changes?after=-1")[0], 400)
        self.assertEqual(self.request("GET", "/v1/tasks")[1]["tasks"], [])

    def test_duplicate_mutation_keys_fail_closed_without_consuming_receipts(self):
        def raw_request(method, path, payload, headers):
            request = Request(
                self.origin + path, data=payload.encode("utf-8"), method=method,
                headers={
                    "Authorization": "Bearer " + TOKEN,
                    "Content-Type": "application/json",
                    **headers,
                },
            )
            try:
                response = urlopen(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.loads(response.read())

        status, error = raw_request(
            "POST", "/v1/tasks", '{"title":"First","title":"Second"}',
            {"Idempotency-Key": "duplicate-create-0001"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(error["error"], "Duplicate JSON object field")
        self.assertEqual(self.request("GET", "/v1/changes")[1]["changes"], [])

        # JSON-escaped property names must not bypass duplicate detection.
        status, _ = raw_request(
            "POST", "/v1/tasks", r'{"title":"First","\u0074itle":"Second"}',
            {"Idempotency-Key": "duplicate-escaped-0001"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.request("GET", "/v1/tasks")[1]["tasks"], [])

        status, created, _ = self.create("Kept", key="duplicate-create-0001")
        self.assertEqual(status, 201)
        path = "/v1/tasks/" + created["id"]
        status, _ = raw_request(
            "PATCH", path, '{"priority":1,"priority":2}',
            {"If-Match": "1", "Idempotency-Key": "duplicate-patch-0001"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.request("GET", path)[1]["revision"], 1)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 1)
        status, updated, _ = self.request(
            "PATCH", path, {"priority": 2},
            headers={"If-Match": "1", "Idempotency-Key": "duplicate-patch-0001"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["priority"], 2)

    def test_nonstandard_json_constants_and_case_aliases_rejected(self):
        def raw_request(method, path, payload, headers):
            req = Request(
                self.origin + path, data=payload.encode("utf-8"), method=method,
                headers={
                    "Authorization": "Bearer " + TOKEN,
                    "Content-Type": "application/json", **headers,
                },
            )
            try:
                response = urlopen(req, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.loads(response.read())

        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                status, error = raw_request(
                    "POST", "/v1/tasks", '{"title":"Unsafe","priority":' + constant + '}',
                    {"Idempotency-Key": "nonfinite-create-0001"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(error["error"], "Non-standard JSON numeric constant")

        # A similarly named field with distinct case must not be interpreted as "title".
        status, error = raw_request(
            "POST", "/v1/tasks", '{"title":"Valid","Title":"Unexpected"}',
            {"Idempotency-Key": "case-alias-create-0001"},
        )
        self.assertEqual(status, 422)
        self.assertEqual(error["error"], "Unsupported task field")
        self.assertEqual(self.request("GET", "/v1/tasks")[1]["tasks"], [])
        self.assertEqual(self.request("GET", "/v1/changes")[1]["changes"], [])

        # A rejected request must not consume its retry key or write any rows.
        status, created, _ = self.create("Safe", key="nonfinite-create-0001")
        self.assertEqual(status, 201)
        path = "/v1/tasks/" + created["id"]
        status, error = raw_request(
            "PATCH", path, '{"priority":NaN}',
            {"If-Match": "1", "Idempotency-Key": "nonfinite-patch-0001"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(error["error"], "Non-standard JSON numeric constant")
        self.assertEqual(self.request("GET", path)[1]["revision"], 1)
        status, updated, _ = self.request(
            "PATCH", path, {"priority": 1},
            headers={"If-Match": "1", "Idempotency-Key": "nonfinite-patch-0001"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 2)

    def test_unpaired_unicode_rejected_without_persisting_changes(self):
        malformed = "Malformed " + chr(0xD800)
        status, response, _ = self.create(malformed, key="invalid-unicode-0001")
        self.assertEqual(status, 422)
        self.assertIn("Unicode", response["error"])
        self.assertEqual(self.request("GET", "/v1/tasks")[1]["tasks"], [])
        self.assertEqual(self.request("GET", "/v1/changes")[1]["changes"], [])
        status, valid, _ = self.create("Working", key="valid-unicode-0002")
        self.assertEqual(status, 201)
        path = "/v1/tasks/" + valid["id"]
        status, _, _ = self.request(
            "PATCH", path, {"title": malformed}, headers={"If-Match": "1"}
        )
        self.assertEqual(status, 422)
        self.assertEqual(self.request("GET", path)[1]["revision"], 1)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 1)

    def test_concurrent_replay_creates_one_task(self):
        def attempt(_):
            return self.create("One copy only", key="concurrent-key-0001")
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(attempt, range(5)))
        self.assertEqual([status for status, _, _ in results], [201] * 5)
        self.assertEqual(len({response["id"] for _, response, _ in results}), 1)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 1)

    def test_private_sqlite_permissions_and_symlink_rejection(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        alias = Path(self.tmp.name) / "alias.sqlite3"
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            TaskDatabase(alias)

    def test_persists_across_store_reopens(self):
        self.create("Persistent")
        reopened = TaskDatabase(self.path)
        self.assertEqual(len(reopened.list_tasks()), 1)
        self.assertEqual(len(reopened.changes()["changes"]), 1)


if __name__ == "__main__":
    unittest.main()
