"""Raw HTTP precondition/framing tests against synthetic loopback Tasks only."""
import json
import socket
import sqlite3
import unittest
from test_api import ApiTest, TOKEN

CRLF = bytes([13, 10])


class RawHeaderTests(unittest.TestCase):
    setUp = ApiTest.setUp
    tearDown = ApiTest.tearDown
    request = ApiTest.request
    create = ApiTest.create
    def raw(self, method, route, headers, body=b""):
        lines = [f"{method} {route} HTTP/1.1",
                 "Host: 127.0.0.1", "Connection: close", *headers]
        data = CRLF.join(line.encode("ascii") for line in lines) + CRLF * 2 + body
        with socket.create_connection(("127.0.0.1", self.server.server_port), timeout=3) as sock:
            sock.settimeout(3)
            sock.sendall(data)
            output = b""
            while True:
                part = sock.recv(8192)
                if not part:
                    break
                output += part
        code = int(output.split(CRLF, 1)[0].split()[1])
        return code, json.loads(output.split(CRLF * 2, 1)[1])

    def auth(self):
        return ["Authorization: Bearer " + TOKEN]

    def assert_untouched(self):
        self.assertEqual(self.store.bootstrap(), {"schemaVersion": 1, "tasks": [], "cursor": 0})
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0], 0)

    def test_malformed_mutation_headers_do_not_create_task_or_receipts(self):
        valid = self.auth() + ["Content-Type: application/json",
                               "Content-Length: 16",
                               "Idempotency-Key: framing-0001"]
        payload = b'{"title":"Safe"}'
        self.assertEqual(len(payload), 16)
        cases = [
            valid + ["Content-Length: 16"],
            valid + ["Content-Length: 25"],
            valid + ["Content-Type: application/json"],
            valid + ["Content-Type: text/plain"],
            valid + ["Transfer-Encoding: chunked"],
            valid + ["Transfer-Encoding: identity"],
            [h for h in valid if not h.startswith("Content-Length:")],
            [h for h in valid if not h.startswith("Content-Length:")] + ["Content-Length: +16"],
            valid + ["Idempotency-Key: framing-0002"],
        ]
        for fields in cases:
            with self.subTest(fields=fields):
                code, payload_or_error = self.raw("POST", "/v1/tasks", fields, payload)
                self.assertIn(code, (400, 413, 415), payload_or_error)
                self.assert_untouched()
        # Rejected requests never consume the original retry key.
        code, created = self.raw("POST", "/v1/tasks", valid, payload)
        self.assertEqual(code, 201)
        self.assertEqual(created["title"], "Safe")
        self.assertEqual(self.store.bootstrap()["cursor"], 1)

    def test_ambiguous_if_match_and_mutation_retry_key_do_not_update_or_delete(self):
        created = self.create("Existing", key="existing-0001")[1]
        uri = "/v1/tasks/" + created["id"]
        field = self.auth() + ["If-Match: 1", "Idempotency-Key: update-0001",
                               "Content-Type: application/json", "Content-Length: 17"]
        update_body = b'{"title":"Change"}'
        self.assertEqual(len(update_body), 18)
        # Content-Length must match actual mutation to ensure this reaches precondition checks.
        field[-1] = "Content-Length: " + str(len(update_body))
        self.assertEqual(self.raw("PATCH", uri, field + ["If-Match: 1"], update_body)[0], 428)
        self.assertEqual(self.raw("PATCH", uri, field + ["Idempotency-Key: update-0002"], update_body)[0], 400)
        self.assertEqual(self.raw("DELETE", uri, self.auth() + ["If-Match: 1", "If-Match: 1"])[0], 428)
        self.assertEqual(self.raw("DELETE", uri, self.auth() + ["If-Match: 1",
                "Idempotency-Key: delete-0001", "Idempotency-Key: delete-0002"])[0], 400)
        self.assertEqual(self.store.get_task(created["id"])["revision"], 1)
        self.assertEqual(self.store.bootstrap()["cursor"], 1)
        status, updated, _ = self.request("PATCH", uri, {"title": "Change"},
                                           headers={"If-Match": "1", "Idempotency-Key": "update-0001"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)

    def test_repeated_authorization_never_chooses_a_valid_credential(self):
        for auth_headers in (
            ["Authorization: Bearer " + TOKEN, "Authorization: Bearer wrong"],
            ["Authorization: Bearer wrong", "Authorization: Bearer " + TOKEN],
        ):
            code, details = self.raw("GET", "/v1/bootstrap", auth_headers)
            self.assertEqual(code, 401, details)
        self.assert_untouched()
