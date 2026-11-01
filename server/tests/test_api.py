"""No external network, credentials or real user data are used by API tests."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import TaskDatabase, make_handler

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

    def test_created_tasks_idempotency_and_conflicting_key(self):
        status, first, _ = self.create("Launch", priority=1, due="2026-11-07")
        self.assertEqual(status, 201)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["due"], "2026-11-07")
        self.assertEqual(self.create("Launch", priority=1, due="2026-11-07")[1], first)
        self.assertEqual(self.create("Different")[0], 409)
        self.assertEqual(len(self.request("GET", "/v1/tasks")[1]["tasks"]), 1)
        self.assertEqual(len(self.request("GET", "/v1/changes")[1]["changes"]), 1)

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
