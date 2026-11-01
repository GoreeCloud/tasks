"""Local-only authenticated Tasks API prototype.

NOT A PRODUCTION SERVICE. Enforces 127.0.0.1 binding and a preconfigured bearer
token; no browser CORS, TLS termination, multi-user tenancy or cloud sync yet.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timezone
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

MAX_BODY = 64 * 1024
KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
TASK_ID_PATTERN = re.compile(r"^[0-9a-f-]{36}$")


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalized_date(value):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ApiError(422, "due must be a valid YYYY-MM-DD date or null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ApiError(422, "due must be a valid YYYY-MM-DD date or null") from error
    if parsed.isoformat() != value:
        raise ApiError(422, "due must be a valid YYYY-MM-DD date or null")
    return value


def normalize_task_fields(body: object, *, create: bool) -> dict:
    if not isinstance(body, dict) or (not body and not create):
        raise ApiError(422, "Expected a non-empty task JSON object")
    allowed = {"title", "priority", "due"} if create else {"title", "priority", "due", "completed"}
    if set(body) - allowed:
        raise ApiError(422, "Unsupported task field")
    if create and "title" not in body:
        raise ApiError(422, "title is required")
    fields = {}
    if "title" in body:
        title = body["title"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 240:
            raise ApiError(422, "title must be 1–240 characters")
        fields["title"] = title.strip()
    if "priority" in body or create:
        priority = body.get("priority", 4)
        if type(priority) is not int or not 1 <= priority <= 4:
            raise ApiError(422, "priority must be an integer from 1 to 4")
        fields["priority"] = priority
    if "due" in body or create:
        fields["due"] = normalized_date(body.get("due"))
    if "completed" in body:
        if type(body["completed"]) is not bool:
            raise ApiError(422, "completed must be a boolean")
        fields["completed"] = body["completed"]
    return fields


def snapshot(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "title": row["title"], "priority": row["priority"],
        "due": row["due"], "completed": bool(row["completed"]),
        "revision": row["revision"], "createdAt": row["created_at"],
        "updatedAt": row["updated_at"], "deleted": bool(row["deleted"])
    }


class TaskDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    due TEXT,
                    completed INTEGER NOT NULL DEFAULT 0,
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS changes (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency (
                    request_key TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_open ON tasks(deleted, completed, priority);
            """)
            db.commit()

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def _record_change(self, db: sqlite3.Connection, task: dict, action: str):
        db.execute(
            "INSERT INTO changes(task_id,operation,snapshot_json) VALUES (?,?,?)",
            (task["id"], action, json.dumps(task, separators=(",", ":")))
        )

    def list_tasks(self, limit: int = 100) -> list[dict]:
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT * FROM tasks WHERE deleted=0 ORDER BY completed,priority,created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [snapshot(row) for row in rows]

    def get_task(self, task_id: str) -> dict:
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM tasks WHERE id=? AND deleted=0", (task_id,)).fetchone()
        if row is None:
            raise ApiError(404, "Task not found")
        return snapshot(row)

    def create_task(self, body: object, key: str) -> dict:
        if not KEY_PATTERN.fullmatch(key):
            raise ApiError(400, "Idempotency-Key must contain 8–128 allowed characters")
        fields = normalize_task_fields(body, create=True)
        canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT payload_hash,response_json FROM idempotency WHERE request_key=?", (key,)
            ).fetchone()
            if previous:
                if not hmac.compare_digest(previous["payload_hash"], digest):
                    db.rollback()
                    raise ApiError(409, "Idempotency-Key was reused with different data")
                db.rollback()
                return json.loads(previous["response_json"])
            now = utc_now()
            task_id = str(uuid4())
            db.execute(
                "INSERT INTO tasks(id,title,priority,due,completed,revision,created_at,updated_at,deleted) "
                "VALUES (?,?,?,?,0,1,?,?,0)",
                (task_id, fields["title"], fields["priority"], fields["due"], now, now)
            )
            created = snapshot(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
            self._record_change(db, created, "created")
            db.execute(
                "INSERT INTO idempotency(request_key,payload_hash,response_json) VALUES (?,?,?)",
                (key, digest, json.dumps(created))
            )
            db.commit()
        return created

    def update_task(self, task_id: str, body: object, expected_revision: int) -> dict:
        fields = normalize_task_fields(body, create=False)
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM tasks WHERE id=? AND deleted=0", (task_id,)).fetchone()
            if not previous:
                db.rollback()
                raise ApiError(404, "Task not found")
            if previous["revision"] != expected_revision:
                db.rollback()
                raise ApiError(409, "Task revision conflict; refresh before changing")
            data = snapshot(previous)
            data.update(fields)
            now = utc_now()
            db.execute(
                "UPDATE tasks SET title=?, priority=?, due=?, completed=?, revision=?, updated_at=? WHERE id=?",
                (data["title"], data["priority"], data["due"], int(data["completed"]),
                 expected_revision + 1, now, task_id)
            )
            updated = snapshot(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
            self._record_change(db, updated, "updated")
            db.commit()
        return updated

    def delete_task(self, task_id: str, expected_revision: int) -> dict:
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM tasks WHERE id=? AND deleted=0", (task_id,)).fetchone()
            if not previous:
                db.rollback()
                raise ApiError(404, "Task not found")
            if previous["revision"] != expected_revision:
                db.rollback()
                raise ApiError(409, "Task revision conflict; refresh before deleting")
            db.execute(
                "UPDATE tasks SET deleted=1, revision=?, updated_at=? WHERE id=?",
                (expected_revision + 1, utc_now(), task_id)
            )
            tombstone = snapshot(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
            self._record_change(db, tombstone, "deleted")
            db.commit()
        return tombstone

    def changes(self, after: int = 0, limit: int = 100) -> dict:
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT seq,operation,snapshot_json FROM changes WHERE seq>? ORDER BY seq ASC LIMIT ?",
                (after, limit + 1)
            ).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        return {
            "changes": [{
                "seq": row["seq"], "operation": row["operation"],
                "task": json.loads(row["snapshot_json"])
            } for row in rows],
            "cursor": rows[-1]["seq"] if rows else after,
            "hasMore": has_more
        }


def make_handler(store: TaskDatabase, secret: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GoreeCloudTasksDevAPI/0.1"
        sys_version = ""

        def setup(self):
            self.request.settimeout(10)
            super().setup()

        def log_message(self, _fmt, *_args):
            # Do not log request paths or task content.
            pass

        def reply(self, status: int, value: dict):
            raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(raw)

        def authorize(self):
            provided = self.headers.get("Authorization", "")
            try:
                authorized = hmac.compare_digest(provided, "Bearer " + secret)
            except (TypeError, UnicodeError):
                authorized = False
            if not authorized:
                raise ApiError(401, "Authorization required")

        def body_json(self) -> object:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json" or "Transfer-Encoding" in self.headers:
                raise ApiError(415, "Expected Content-Type: application/json with Content-Length")
            length = self.headers.get("Content-Length", "")
            if len(length) > 5 or not length.isascii() or not length.isdecimal() or not 0 < int(length) <= MAX_BODY:
                raise ApiError(413, "JSON request must be between 1 and 65536 bytes")
            try:
                return json.loads(self.rfile.read(int(length)).decode("utf-8"))
            except (UnicodeError, ValueError) as error:
                raise ApiError(400, "Invalid UTF-8 JSON document") from error

        def revision(self) -> int:
            value = self.headers.get("If-Match", "")
            if len(value) > 10 or not value.isascii() or not value.isdecimal() or not 0 < int(value) < 2**31:
                raise ApiError(428, "If-Match must specify the current task revision")
            return int(value)

        def dispatch(self, method: str):
            parsed = urlsplit(self.path)
            route = parsed.path
            if route == "/healthz" and method == "GET":
                self.reply(200, {"status": "ok", "mode": "loopback-development"})
                return
            self.authorize()
            if route == "/v1/tasks" and method == "GET":
                limit = self.positive_limit(parsed.query)
                self.reply(200, {"tasks": store.list_tasks(limit), "limit": limit})
                return
            if route == "/v1/tasks" and method == "POST":
                key = self.headers.get("Idempotency-Key", "")
                created = store.create_task(self.body_json(), key)
                self.reply(201, created)
                return
            if route == "/v1/changes" and method == "GET":
                query = parse_qs(parsed.query, keep_blank_values=True)
                if set(query) - {"after", "limit"}:
                    raise ApiError(400, "Unknown change cursor query")
                after_raw = query.get("after", ["0"])
                if len(after_raw) != 1 or len(after_raw[0]) > 19 or not after_raw[0].isascii() or not after_raw[0].isdecimal() or int(after_raw[0]) >= 2**63:
                    raise ApiError(400, "after must be a nonnegative change cursor")
                limit_raw = query.get("limit", ["100"])
                if len(limit_raw) != 1 or len(limit_raw[0]) > 3 or not limit_raw[0].isascii() or not limit_raw[0].isdecimal() or not 1 <= int(limit_raw[0]) <= 100:
                    raise ApiError(400, "limit must be between 1 and 100")
                self.reply(200, store.changes(int(after_raw[0]), int(limit_raw[0])))
                return
            match = re.fullmatch(r"/v1/tasks/([0-9a-f-]{36})", route)
            if match:
                task_id = match.group(1)
                if not TASK_ID_PATTERN.fullmatch(task_id):
                    raise ApiError(400, "Invalid task ID")
                if method == "GET":
                    self.reply(200, store.get_task(task_id))
                    return
                if method == "PATCH":
                    updated = store.update_task(task_id, self.body_json(), self.revision())
                    self.reply(200, updated)
                    return
                if method == "DELETE":
                    deleted = store.delete_task(task_id, self.revision())
                    self.reply(200, deleted)
                    return
            raise ApiError(404, "Endpoint not found")

        def positive_limit(self, query_text: str) -> int:
            params = parse_qs(query_text, keep_blank_values=True)
            if set(params) - {"limit"}:
                raise ApiError(400, "Unknown task query")
            raw = params.get("limit", ["100"])
            if len(raw) != 1 or len(raw[0]) > 3 or not raw[0].isascii() or not raw[0].isdecimal() or not 1 <= int(raw[0]) <= 100:
                raise ApiError(400, "limit must be between 1 and 100")
            return int(raw[0])

        def invoke(self, method: str):
            try:
                self.dispatch(method)
            except ApiError as error:
                self.reply(error.status, {"error": error.message})
            except (sqlite3.Error, OSError):
                self.reply(503, {"error": "Local data service unavailable"})

        def do_GET(self):
            self.invoke("GET")

        def do_POST(self):
            self.invoke("POST")

        def do_PATCH(self):
            self.invoke("PATCH")

        def do_DELETE(self):
            self.invoke("DELETE")

    return Handler


def main():
    parser = argparse.ArgumentParser(description="GoreeCloud Tasks experimental loopback API")
    parser.add_argument("--port", type=int, default=3037)
    parser.add_argument("--database", default=None)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    token = os.environ.get("GOREETASKS_API_TOKEN", "")
    if len(token) < 32 or token.strip() != token or any(c.isspace() for c in token):
        parser.error("Set GOREETASKS_API_TOKEN to a non-whitespace secret of at least 32 characters")
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    location = Path(args.database) if args.database else data_home / "goreecloud-tasks-server" / "tasks.sqlite3"
    os.umask(0o077)
    storage = TaskDatabase(location)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(storage, token))
    server.daemon_threads = True
    print("Development Tasks API listening on loopback only; multi-user and TLS deployment are disabled.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
