"""No outside egress: localhost Tasks API and synthetic untrusted HTTP fixtures."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import TaskDatabase, make_handler
from bootstrap_client import SnapshotChanged, collect_and_seed
from loopback_bootstrap import LoopbackBootstrapTransport, MAX_RESPONSE_BYTES
from outbox import OfflineOutbox, OutboxError

TOKEN = "synthetic-loopback-bootstrap-token-1234567890"


class LoopbackTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = TaskDatabase(self.root / "api.sqlite3")
        self.outbox = OfflineOutbox(self.root / "local.sqlite3")
        self.api = ThreadingHTTPServer(("127.0.0.1", 0),
            make_handler(self.source, TOKEN))
        self.api.daemon_threads = True
        self.thread = threading.Thread(target=self.api.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.api.shutdown()
        self.api.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def client(self, token=TOKEN):
        return LoopbackBootstrapTransport(self.api.server_port, token)

    def test_full_local_http_bootstrap_over_100_and_delta_cursor(self):
        items = [
            self.source.create_task({"title": "Synthetic %d" % i},
                                    "http-bootstrap-%05d" % i)
            for i in range(103)
        ]
        client = self.client()
        self.assertNotIn(TOKEN, repr(client))
        self.assertEqual(collect_and_seed(self.outbox, client.fetch_page, limit=23), 103)
        self.assertEqual(self.outbox.cursor(), 103)
        self.assertTrue(all(self.outbox.remote_task(item["id"]) == item
                            for item in items))
        edited = self.source.update_task(items[0]["id"], {"title": "After sync"}, 1)
        self.assertEqual(self.outbox.apply_change_page(self.source.changes(after=103), 103), 104)
        self.assertEqual(self.outbox.remote_task(items[0]["id"])["title"], edited["title"])

    def test_http_409_maps_to_checkpoint_restart_with_no_partial_writes(self):
        tasks = [
            self.source.create_task({"title": "Before %d" % i},
                                    "conflict-bootstrap-%04d" % i)
            for i in range(3)
        ]
        client = self.client()
        calls = 0
        def mutating_fetch(**params):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.source.update_task(tasks[0]["id"], {"title": "Changed"}, 1)
            return client.fetch_page(**params)
        self.assertEqual(collect_and_seed(self.outbox, mutating_fetch, limit=2), 4)
        self.assertEqual(calls, 4)
        self.assertEqual(self.outbox.remote_task(tasks[0]["id"])["title"], "Changed")

    def test_auth_and_constructor_fail_closed(self):
        for token in ("short", TOKEN + "\r", TOKEN + "\n", TOKEN + " ", "é" * 40):
            with self.subTest(token=token[:4]), self.assertRaises(OutboxError):
                LoopbackBootstrapTransport(3037, token)
        for port in (0, -1, 65536, True, "3037"):
            with self.subTest(port=port), self.assertRaises(OutboxError):
                LoopbackBootstrapTransport(port, TOKEN)
        for value in (0, -1, 11, False, float("nan"), float("inf")):
            with self.subTest(timeout=value), self.assertRaises(OutboxError):
                LoopbackBootstrapTransport(3037, TOKEN, timeout=value)
        with self.assertRaises(OutboxError):
            self.client("wrong-" + TOKEN).fetch_page(limit=1, after=None, checkpoint=None)
        with self.assertRaises(OutboxError):
            self.client().fetch_page(limit=1, after=str(uuid4()), checkpoint=None)
        with self.assertRaises(OutboxError):
            self.client().fetch_page(limit=1, after=None, checkpoint=0)
        self.assertEqual(self.outbox.cursor(), 0)

    def _serve_stub(self, status, body, headers):
        seen = []
        class Stub(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.path)
                self.send_response(status)
                for key, value in headers:
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, seen

    def test_redirect_malformed_json_headers_and_oversize_are_denied(self):
        valid_body = json.dumps({"schemaVersion": 1, "tasks": [], "limit": 1,
                                 "checkpoint": 0, "nextAfter": None,
                                 "hasMore": False}).encode()
        good_headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(valid_body))),
            ("Cache-Control", "no-store"),
        ]
        cases = [
            (302, b"", [("Location", "https://external.example.invalid/private"),
                         ("Content-Length", "0")]),
            (200, valid_body, good_headers + [("Content-Length", str(len(valid_body)))]),
            (200, valid_body, good_headers + [("Transfer-Encoding", "chunked")]),
            (200, valid_body, good_headers + [("Content-Encoding", "gzip")]),
            (200, valid_body, [("Content-Type", "text/html"),
                              ("Content-Length", str(len(valid_body))),
                              ("Cache-Control", "no-store")]),
            (200, valid_body, [("Content-Type", "application/json; charset=utf-8"),
                              ("Content-Length", str(len(valid_body) + 1)),
                              ("Cache-Control", "no-store")]),
            (200, b'{"a":1,"a":2}', [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", "13"), ("Cache-Control", "no-store")]),
            (200, b'{"checkpoint":NaN}', [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", "18"), ("Cache-Control", "no-store")]),
            (200, valid_body, [("Content-Type", "application/json; charset=utf-8"),
                               ("Content-Length", str(MAX_RESPONSE_BYTES + 1)),
                               ("Cache-Control", "no-store")]),
        ]
        for status, body, headers in cases:
            server, thread, seen = self._serve_stub(status, body, headers)
            try:
                client = LoopbackBootstrapTransport(server.server_port, TOKEN)
                with self.subTest(status=status, headers=headers), self.assertRaises(OutboxError):
                    client.fetch_page(limit=1, after=None, checkpoint=None)
                self.assertEqual(len(seen), 1)
                self.assertEqual(self.outbox.cursor(), 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
