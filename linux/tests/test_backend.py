"""Native Linux backend logic tests; no filesystem changes or real API traffic."""
import json
import sys
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QCoreApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import TasksBackend  # noqa: E402


class TasksBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.backend = TasksBackend("http://127.0.0.1:8000",
                                    "mock-token-only-for-unittest-not-real-12345")
        today = date.today()
        self.backend._all_tasks = [
            dict(id="1", title="Pay rent", description="", tags=["home"],
                 project_id="p", due_date=today.isoformat(), completed_at=None),
            dict(id="2", title="Read book", description="Work notes", tags=["work"],
                 project_id="q", due_date=(today + timedelta(days=3)).isoformat(),
                 completed_at=None),
            dict(id="3", title="Past task", description="", tags=["home"],
                 project_id="p", due_date=(today - timedelta(days=3)).isoformat(),
                 completed_at="2026-11-20T00:00:00Z"),
            dict(id="4", title="No deadline", description="", tags=[],
                 project_id=None, due_date=None, completed_at=None),
        ]
        self.backend._apply_filters()

    def test_filter_status_date_and_project(self):
        self.assertEqual(len(self.backend.tasks), 3)
        self.backend.setView("today")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["1"])
        self.backend.setView("upcoming")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["2"])
        self.backend.setView("completed")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["3"])
        self.backend.setView("inbox")
        self.backend.setProjectFilter("p")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["1"])

    def test_search_and_invalid_view(self):
        self.backend.setSearch("HOME")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["1"])
        self.backend.setSearch("work notes")
        self.assertEqual([t["id"] for t in self.backend.tasks], ["2"])
        self.backend.setView("no-such-view")
        self.assertEqual(self.backend.error, "Unknown task view")

    def test_habit_response_and_empty_model(self):
        self.assertEqual(self.backend.habits, [])
        sample = {"id": "fixture", "name": "Read", "checked_in_today": False,
                  "current_streak": 3, "total_checkins": 7, "version": 2}
        self.backend._update_habits([sample])
        self.assertEqual(self.backend.habits[0]["current_streak"], 3)
        self.backend._update_habits({"bad": "shape"})
        self.assertEqual(self.backend.error, "Invalid habit list response")
        self.assertEqual(self.backend.habits[0]["name"], "Read")

    def test_task_fields_reject_bad_inputs(self):
        mk = TasksBackend._task_data
        value = mk(" Task ", "notes", 2, "2026-11-21", "weekly", "", "Home,home")
        self.assertEqual(value["tags"], ["home"])
        self.assertEqual(value["title"], "Task")
        subtask = mk("Child", "", 2, "", "none", "", "", "existing-parent-id")
        self.assertEqual(subtask["parent_id"], "existing-parent-id")
        self.assertIsNone(value["project_id"])
        for cadence in ("weekdays", "biweekly", "yearly"):
            with self.subTest(cadence=cadence):
                new = mk("Recurring", "", 2, "2026-11-20", cadence, "", "")
                self.assertEqual(new["recurrence"], cadence)
                with self.assertRaises(ValueError):
                    mk("Missing due", "", 2, "", cadence, "", "")
        for args in [
            (" ", "", 2, "", "none", "", ""),
            ("Hi", "", 8, "", "none", "", ""),
            ("Hi", "", 2, "", "daily", "", ""),
            ("Hi", "", 2, "2026-02-30", "none", "", ""),
            ("Hi", "", 2, "", "bogus", "", ""),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                mk(*args)



    def test_consistent_snapshot_full_and_fail_closed(self):
        base = dict(id="placeholder", title="Private", description="", tags=[],
                    project_id="project-1", due_date=None, completed_at=None)
        tasks = [{**base, "id": f"synthetic-{i}", "title": f"Task {i}"} for i in range(1005)]
        snapshot = dict(format="goreecloud-tasks-sync-1", cursor=42,
                        tasks=tasks, projects=[dict(id="project-1", name="Testing")])
        self.backend._apply_snapshot(snapshot)
        self.assertEqual(len(self.backend.tasks), 1005)
        self.assertEqual(len(self.backend.allTasks), 1005)
        self.assertEqual(self.backend.projects[0]["name"], "Testing")

        previous = list(self.backend.allTasks)
        previous_projects = list(self.backend.projects)
        for invalid in [
            None,
            dict(format="unknown", cursor=42, tasks=tasks, projects=[]),
            dict(format="goreecloud-tasks-sync-1", cursor=-1, tasks=[], projects=[]),
            dict(format="goreecloud-tasks-sync-1", cursor=42, tasks=tasks, projects=[{"id": 7}]),
            dict(format="goreecloud-tasks-sync-1", cursor=42, tasks=tasks + [None], projects=[]),
            dict(format="goreecloud-tasks-sync-1", cursor=42,
                 tasks=tasks * 6, projects=[]),
        ]:
            with self.subTest(invalid_type=type(invalid).__name__):
                self.backend._apply_snapshot(invalid)
                self.assertEqual(self.backend.allTasks, previous)
                self.assertEqual(self.backend.projects, previous_projects)

    def test_refresh_uses_single_atomic_bootstrap_request(self):
        calls = []
        self.backend._request = lambda method, path, callback=None: calls.append(
            (method, path, callback)
        )
        self.backend.refresh()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0:2], ("GET", "/sync/bootstrap"))
        self.assertEqual(calls[0][2], self.backend._apply_snapshot)

    def test_habit_edit_validates_input_and_sends_one_versioned_patch(self):
        calls = []
        self.backend._request = lambda method, path, payload=None, callback=None: (
            calls.append((method, path, payload, callback))
        )
        self.backend.editHabit("habit with spaces", 4, "  Read  ", "Daily notes")
        self.assertEqual(len(calls), 1)
        method, path, payload, callback = calls[0]
        self.assertEqual((method, path), ("PATCH", "/habits/habit%20with%20spaces"))
        self.assertEqual(payload, {
            "expected_version": 4, "name": "Read", "description": "Daily notes"
        })
        self.assertTrue(callable(callback))
        for bad in [
            ("habit-1", 4, "  ", "notes"),
            ("habit-1", 0, "Read", "notes"),
            ("habit-1", 4, "Read", "x" * 16001),
            ("habit-1", 4, "x" * 121, "notes"),
            ("", 4, "Read", "notes"),
        ]:
            with self.subTest(bad=bad[:3]):
                self.backend.editHabit(*bad)
                self.assertEqual(len(calls), 1, "Invalid input must not issue an API call")

    def test_habit_history_bounds_paging_and_stale_callback(self):
        calls = []
        self.backend._request = lambda method, path, callback=None: calls.append(
            (method, path, callback)
        )
        self.backend.loadHabitHistory("habit with spaces", -1)
        self.backend.loadHabitHistory("", 0)
        self.assertEqual(calls, [])
        self.backend.loadHabitHistory("habit with spaces", 0)
        self.assertEqual(calls[0][:2], (
            "GET", "/habits/habit%20with%20spaces/checkins?limit=30&offset=0"
        ))
        expected = [(date(2026, 11, 20) - timedelta(days=i)).isoformat()
                    for i in range(30)]
        calls[0][2](expected)
        self.assertEqual(self.backend.habitHistory, expected)
        self.assertTrue(self.backend.habitHistoryHasMore)
        self.assertEqual(self.backend.habitHistoryOffset, 0)
        self.backend.loadHabitHistory("habit with spaces", 30)
        self.assertEqual(calls[1][1],
                         "/habits/habit%20with%20spaces/checkins?limit=30&offset=30")
        self.assertEqual(self.backend.habitHistory, [])
        calls[0][2](expected)
        self.assertEqual(self.backend.habitHistory, [],
                         "Stale network callbacks must not restore previous dates")
        calls[1][2](["2026-10-21", "2026-10-20"])
        self.assertEqual(self.backend.habitHistory, ["2026-10-21", "2026-10-20"])
        self.assertFalse(self.backend.habitHistoryHasMore)
        self.assertEqual(self.backend.habitHistoryOffset, 30)
        for bad in [None, {"bad": "shape"}, ["2026-10-22", "2026-10-22"],
                    ["not-a-date"], ["2026-10-20", "2026-10-21"],
                    ["2026-10-20"] * 31]:
            self.backend.loadHabitHistory("habit with spaces", 0)
            calls[-1][2](bad)
            self.assertEqual(self.backend.habitHistory, [],
                             "Malformed history must never update the visible list")
        self.backend.loadHabitHistory("habit with spaces", 0)
        old = calls[-1][2]
        self.backend.clearHabitHistory()
        old(expected)
        self.assertEqual(self.backend.habitHistory, [])



    def test_private_ui_session_connect_and_disconnect_without_network(self):
        self.backend.disconnect()
        self.assertFalse(self.backend.connected)
        self.assertEqual(self.backend.status, "Disconnected")
        secret = "synthetic-dev-only-token-not-real-123456789"
        attempts = [
            ("http://public.example.com", secret),
            ("https://user:password@example.com", secret),
            ("file:///tmp/not-server", secret),
            ("http://127.0.0.1:8000\nX-Header:unsafe", secret),
            ("https://example.com/?key=in-url", secret),
            ("https://example.com", "too-short"),
            ("https://example.com", "x" * 600),
            ("https://example.com", "x" * 32 + "\n"),
            ("https://[unclosed", secret),
        ]
        for url, value in attempts:
            with self.subTest(url=url[:34], size=len(value)):
                self.backend.connectToServer(url, value)
                self.assertFalse(self.backend.connected)
                self.assertEqual(self.backend._all_tasks, [])
        refresh_calls = []
        self.backend.refresh = lambda: refresh_calls.append(True)
        self.backend.connectToServer("http://127.0.0.1:8000", secret)
        self.assertTrue(self.backend.connected)
        self.assertEqual(len(refresh_calls), 1)
        self.backend._all_tasks = [{"id": "private", "title": "synthetic task"}]
        self.backend._tasks = list(self.backend._all_tasks)
        self.backend._projects = [{"id": "project", "name": "Private"}]
        self.backend._habits = [{"id": "habit", "name": "Private routine"}]
        self.backend._habit_history = ["2026-11-20"]
        self.backend._project_filter = "project"
        self.backend._query = "private query"
        class FakeReply:
            aborted = False
            def abort(self): self.aborted = True
        network_reply = FakeReply()
        self.backend._outstanding_replies.add(network_reply)
        generation = self.backend._session_generation
        self.backend.disconnect()
        self.assertGreater(self.backend._session_generation, generation)
        self.assertTrue(network_reply.aborted)
        self.assertFalse(self.backend.connected)
        self.assertEqual(self.backend._token, "")
        self.assertEqual(self.backend._all_tasks, [])
        self.assertEqual(self.backend.tasks, [])
        self.assertEqual(self.backend.projects, [])
        self.assertEqual(self.backend.habits, [])
        self.assertEqual(self.backend.habitHistory, [])
        self.assertEqual(self.backend._project_filter, None)
        self.assertEqual(self.backend._query, "")
        self.assertEqual(self.backend.status, "Disconnected")

    def test_login_requires_secure_urls_and_printable_token(self):
        valid = "a" * 40
        for url in ["https://example.com", "http://127.0.0.1:8000",
                    "http://localhost:8000", "https://[::1]:443"]:
            self.assertTrue(TasksBackend._valid_url(url), url)
        for url in ["http://example.com", "https://user:pass@example.com",
                    "https://host.test?token=yes", "https://host.test/",
                    "http://127.0.0.1:99999", "https://host.test\tbad",
                    "https://[broken", ""]:
            self.assertFalse(TasksBackend._valid_url(url), url)
        self.assertTrue(TasksBackend._valid_token(valid))
        self.assertFalse(TasksBackend._valid_token("a" * 31))
        self.assertFalse(TasksBackend._valid_token("a" * 513))
        self.assertFalse(TasksBackend._valid_token("a" * 40 + " "))
        self.assertFalse(TasksBackend._valid_token("a" * 40 + "\n"))


    def test_authenticated_loopback_refresh_and_disconnect_blocks_late_reply(self):
        token = "synthetic-only-loopback-qt-token-123456789"
        delayed = Event()
        entered = Event()
        release = Event()
        evidence = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                evidence.append((self.path, self.headers.get("Authorization")))
                if delayed.is_set():
                    entered.set()
                    release.wait(timeout=3)
                body = json.dumps({
                    "format": "goreecloud-tasks-sync-1", "cursor": 1,
                    "projects": [{"id": "project", "name": "Synthetic private"}],
                    "tasks": [{
                        "id": "task-1", "title": "Synthetic private",
                        "description": "", "tags": [], "project_id": "project",
                        "completed_at": None, "due_date": None
                    }]
                }).encode("utf-8")
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # A clean disconnect aborts the in-flight HTTP reply.
            def log_message(self, *_args):
                return  # Never log the bearer token or private task text.
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = TasksBackend(f"http://127.0.0.1:{server.server_port}", token)
            client.refresh()
            limit = time.monotonic() + 3
            while time.monotonic() < limit and not client.allTasks:
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertEqual(len(client.allTasks), 1, client.error)
            self.assertEqual(client.projects[0]["name"], "Synthetic private")
            delayed.set()
            client.refresh()
            until_response = time.monotonic() + 3
            while time.monotonic() < until_response and not entered.is_set():
                self.qt.processEvents()
                time.sleep(0.01)
            self.assertTrue(entered.is_set(), "Loopback fixture received no second request")
            before = client._session_generation
            client.disconnect()
            release.set()
            until = time.monotonic() + 0.1
            while time.monotonic() < until:
                self.qt.processEvents()
            self.assertGreater(client._session_generation, before)
            self.assertFalse(client.connected)
            self.assertEqual(client.allTasks, [])
            self.assertEqual(client.projects, [])
            self.assertEqual(client.habits, [])
            self.assertEqual(client.status, "Disconnected")
            self.assertTrue(evidence)
            self.assertTrue(all(path == "/api/v1/sync/bootstrap" and header == "Bearer " + token
                                for path, header in evidence))
        finally:
            release.set()
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
