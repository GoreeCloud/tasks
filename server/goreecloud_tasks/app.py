"""GoreeCloud Tasks: single-user, token-protected, SQLite-backed API.

The development server binds to loopback by default. A production reverse proxy
must provide TLS, rate limiting and identity boundaries. No telemetry is collected.
"""
from __future__ import annotations

import hmac
import json
import os
import sqlite3
from contextlib import contextmanager
from .changefeed import record_change, replay_receipt, save_receipt, scrub_task_history
from .ical import build_calendar
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator, model_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=16000)
    project_id: str | None = None
    parent_id: str | None = None
    due_date: date | None = None
    priority: int = Field(default=2, ge=1, le=4)
    tags: list[str] = Field(default_factory=list, max_length=12)
    recurrence: Literal["none", "daily", "weekly", "monthly"] = "none"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        result = []
        for item in values:
            tag = item.strip().casefold()
            if not 1 <= len(tag) <= 36:
                raise ValueError("Each tag must have 1–36 characters")
            if tag not in result:
                result.append(tag)
        return result

    @model_validator(mode="after")
    def recurrence_has_date(self):
        if self.recurrence != "none" and self.due_date is None:
            raise ValueError("A recurring task needs a due date")
        return self


class TaskPatch(BaseModel):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=16000)
    project_id: str | None = None
    parent_id: str | None = None
    due_date: date | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    tags: list[str] | None = Field(default=None, max_length=12)
    recurrence: Literal["none", "daily", "weekly", "monthly"] | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Title cannot be blank")
        return value.strip() if value is not None else None

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value: list[str] | None) -> list[str] | None:
        return TaskCreate.clean_tags(value) if value is not None else None


class VersionCheck(BaseModel):
    expected_version: int = Field(ge=1)


class Store:
    """Versioned SQLite storage with serialized mutations and auditable change feed."""

    def __init__(self, path: str):
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.open() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, 3):
                raise RuntimeError("Unsupported database version; do not downgrade the server")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                  id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
                  project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                  due_date TEXT, priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 4),
                  tags TEXT NOT NULL, recurrence TEXT NOT NULL, series_id TEXT,
                  completed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                  version INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date, completed_at);
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
            """)
            db.executescript("""
                CREATE TABLE IF NOT EXISTS change_events (
                  cursor INTEGER PRIMARY KEY AUTOINCREMENT,
                  entity TEXT NOT NULL CHECK(entity IN ('task','project')),
                  entity_id TEXT NOT NULL,
                  operation TEXT NOT NULL CHECK(operation IN ('upsert','delete')),
                  payload TEXT,
                  created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_change_events_cursor ON change_events(cursor);
                CREATE TABLE IF NOT EXISTS request_receipts (
                  idempotency_key TEXT PRIMARY KEY,
                  scope TEXT NOT NULL,
                  fingerprint TEXT NOT NULL,
                  response_json TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
            """)
            # Idempotent, additive migration; old task/event/receipt data remains intact.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(tasks)")}
            if "parent_id" not in columns:
                db.execute(
                    "ALTER TABLE tasks ADD COLUMN parent_id TEXT REFERENCES tasks(id) ON DELETE SET NULL"
                )
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id)")
            db.execute("PRAGMA user_version=3")

    @contextmanager
    def open(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level="DEFERRED")
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        # Obtain the writer reservation before reading the expected revision.
        # Otherwise two clients can both pass the stale-version check.
        with self.open() as connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection


def task_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["tags"] = json.loads(result["tags"])
    return result


def create_app(db_path: str | None = None, api_token: str | None = None) -> FastAPI:
    token = api_token if api_token is not None else os.environ.get("GOREECLOUD_TASKS_API_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Set GOREECLOUD_TASKS_API_TOKEN to at least 32 characters")
    db = Store(db_path or os.environ.get("GOREECLOUD_TASKS_DATABASE", "./data/tasks.sqlite3"))
    app = FastAPI(title="GoreeCloud Tasks", version="0.1.0",
                  description="Single-user development API; require TLS before network exposure.")
    router = APIRouter(prefix="/api/v1")

    def require_token(authorization: Annotated[str | None, Header()] = None):
        expected = "Bearer " + token
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Authentication required",
                                headers={"WWW-Authenticate": "Bearer"})

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @router.get("/projects")
    def projects():
        with db.open() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY name COLLATE NOCASE")]

    @router.post("/projects", status_code=201)
    def add_project(
        data: ProjectCreate,
        idempotency_key: str | None = Header(default=None, min_length=8, max_length=128,
                                             pattern=r"^[A-Za-z0-9._~-]+$")
    ):
        scope, payload = "POST /projects", data.model_dump(mode="json")
        with db.transaction() as conn:
            previous = replay_receipt(conn, idempotency_key, scope, payload)
            if previous is not None:
                return previous
            now = utc_now()
            result = {"id": new_id(), "name": data.name, "created_at": now, "updated_at": now}
            conn.execute("INSERT INTO projects VALUES (:id,:name,:created_at,:updated_at)", result)
            record_change(conn, "project", result["id"], "upsert", result, now)
            save_receipt(conn, idempotency_key, scope, payload, result, now)
            return result

    def ensure_project(conn, project_id):
        if project_id and not conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise HTTPException(status_code=422, detail="Unknown project")

    def ensure_parent(conn, parent_id: str | None, task_id: str | None = None):
        """Reject self-parenting, cycles and attempts to nest under a completed task."""
        if parent_id is None:
            return
        if task_id == parent_id:
            raise HTTPException(status_code=422, detail="Task cannot be its own parent")
        row = conn.execute("SELECT id,completed_at FROM tasks WHERE id=?", (parent_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=422, detail="Unknown parent task")
        if row["completed_at"] is not None:
            raise HTTPException(status_code=409, detail="Cannot nest under a completed task")
        if task_id:
            current = parent_id
            checked: set[str] = set()
            while current is not None:
                if current == task_id or current in checked:
                    raise HTTPException(status_code=422, detail="Parent hierarchy would contain a cycle")
                checked.add(current)
                ancestor = conn.execute("SELECT parent_id FROM tasks WHERE id=?", (current,)).fetchone()
                current = ancestor["parent_id"] if ancestor else None
            if len(checked) > 128:
                raise HTTPException(status_code=422, detail="Hierarchy depth exceeds supported limit")

    @router.get("/tasks")
    def tasks(
        status: Literal["active", "completed", "all"] = "active",
        project_id: str | None = None,
        due_before: date | None = None,
        search: str = Query(default="", max_length=120),
        limit: int = Query(default=1000, ge=1, le=1000),
        offset: int = Query(default=0, ge=0, le=1_000_000),
    ):
        where, args = [], []
        if status == "active":
            where.append("completed_at IS NULL")
        if status == "completed":
            where.append("completed_at IS NOT NULL")
        if project_id:
            where.append("project_id=?")
            args.append(project_id)
        if due_before:
            where.append("due_date<=?")
            args.append(due_before.isoformat())
        if search.strip():
            where.append("(instr(lower(title),lower(?))>0 OR instr(lower(description),lower(?))>0)")
            args.extend([search.strip(), search.strip()])
        sql = "SELECT * FROM tasks" + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY (due_date IS NULL), due_date, priority, created_at DESC, id LIMIT ? OFFSET ?"
        with db.open() as conn:
            return [task_dict(r) for r in conn.execute(sql, [*args, limit, offset])]

    @router.post("/tasks", status_code=201)
    def add_task(
        data: TaskCreate,
        idempotency_key: str | None = Header(default=None, min_length=8, max_length=128,
                                             pattern=r"^[A-Za-z0-9._~-]+$")
    ):
        scope, payload = "POST /tasks", data.model_dump(mode="json")
        with db.transaction() as conn:
            previous = replay_receipt(conn, idempotency_key, scope, payload)
            if previous is not None:
                return previous
            now = utc_now()
            result = dict(id=new_id(), **payload, series_id=None, completed_at=None,
                          created_at=now, updated_at=now, version=1)
            ensure_project(conn, result["project_id"])
            ensure_parent(conn, result["parent_id"])
            conn.execute("""
                INSERT INTO tasks
                (id,title,description,project_id,due_date,priority,tags,recurrence,series_id,
                 completed_at,created_at,updated_at,version,parent_id)
                VALUES (:id,:title,:description,:project_id,:due_date,:priority,:tags,:recurrence,
                        :series_id,:completed_at,:created_at,:updated_at,:version,:parent_id)
            """, {**result, "tags": json.dumps(result["tags"])})
            record_change(conn, "task", result["id"], "upsert", result, now)
            save_receipt(conn, idempotency_key, scope, payload, result, now)
            return result

    def get_existing(conn, task_id: str):
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_dict(row)

    def check_revision(row: dict, expected: int):
        if row["version"] != expected:
            raise HTTPException(status_code=409, detail="Task changed; reload and retry")

    @router.get("/tasks/{task_id}")
    def get_task(task_id: str):
        with db.open() as conn:
            return get_existing(conn, task_id)

    @router.patch("/tasks/{task_id}")
    def edit_task(task_id: str, patch: TaskPatch):
        with db.transaction() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, patch.expected_version)
            if previous["completed_at"]:
                raise HTTPException(status_code=409, detail="Reopen before editing")
            edits = patch.model_dump(exclude_unset=True, exclude={"expected_version"}, mode="json")
            candidate = TaskCreate.model_validate({**{k: previous[k] for k in TaskCreate.model_fields}, **edits})
            data = candidate.model_dump(mode="json")
            ensure_project(conn, data["project_id"])
            ensure_parent(conn, data["parent_id"], task_id=task_id)
            next_version, now = previous["version"] + 1, utc_now()
            conn.execute("""
                UPDATE tasks SET title=:title,description=:description,project_id=:project_id,
                due_date=:due_date,priority=:priority,tags=:tags,recurrence=:recurrence,
                parent_id=:parent_id,updated_at=:now,version=:version WHERE id=:id
            """, {**data, "id": task_id, "tags": json.dumps(data["tags"]),
                  "now": now, "version": next_version})
            changed = get_existing(conn, task_id)
            record_change(conn, "task", task_id, "upsert", changed, now)
            return changed

    @router.post("/tasks/{task_id}/complete")
    def complete_task(
        task_id: str, check: VersionCheck,
        idempotency_key: str | None = Header(default=None, min_length=8, max_length=128,
                                             pattern=r"^[A-Za-z0-9._~-]+$")
    ):
        scope, payload = "POST /tasks/" + task_id + "/complete", check.model_dump(mode="json")
        with db.transaction() as conn:
            replay = replay_receipt(conn, idempotency_key, scope, payload)
            if replay is not None:
                return replay
            previous = get_existing(conn, task_id)
            check_revision(previous, check.expected_version)
            if previous["completed_at"]:
                raise HTTPException(status_code=409, detail="Task already completed")
            if conn.execute("""
                WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM tasks WHERE parent_id=?
                    UNION
                    SELECT child.id FROM tasks child JOIN descendants ON child.parent_id=descendants.id
                )
                SELECT 1 FROM tasks WHERE id IN (SELECT id FROM descendants)
                AND completed_at IS NULL LIMIT 1
            """, (task_id,)).fetchone():
                raise HTTPException(status_code=409, detail="Complete subtasks before parent")
            now = utc_now()
            conn.execute("UPDATE tasks SET completed_at=?,updated_at=?,version=version+1 WHERE id=?",
                         (now, now, task_id))
            next_task = None
            if previous["recurrence"] != "none" and previous["due_date"]:
                due = date.fromisoformat(previous["due_date"])
                if previous["recurrence"] == "daily":
                    due += relativedelta(days=1)
                elif previous["recurrence"] == "weekly":
                    due += relativedelta(weeks=1)
                else:
                    due += relativedelta(months=1)
                new_row = {**previous, "id": new_id(), "due_date": due.isoformat(),
                           "series_id": previous["series_id"] or previous["id"],
                           "completed_at": None, "created_at": now, "updated_at": now, "version": 1}
                conn.execute("""
                    INSERT INTO tasks (
                        id,title,description,project_id,due_date,priority,tags,recurrence,
                        series_id,completed_at,created_at,updated_at,version,parent_id
                    ) VALUES (
                        :id,:title,:description,:project_id,:due_date,:priority,:tags,:recurrence,
                        :series_id,:completed_at,:created_at,:updated_at,:version,:parent_id
                    )
                """, {**new_row, "tags": json.dumps(new_row["tags"])})
                next_task = new_row
                record_change(conn, "task", new_row["id"], "upsert", next_task, now)
            completed = get_existing(conn, task_id)
            record_change(conn, "task", task_id, "upsert", completed, now)
            response = {"completed": completed, "next_task": next_task}
            save_receipt(conn, idempotency_key, scope, payload, response, now)
            return response

    @router.post("/tasks/{task_id}/reopen")
    def reopen_task(task_id: str, check: VersionCheck):
        with db.transaction() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, check.expected_version)
            if not previous["completed_at"]:
                raise HTTPException(status_code=409, detail="Task is already active")
            if previous["parent_id"] is not None:
                ensure_parent(conn, previous["parent_id"], task_id=task_id)
            conn.execute("UPDATE tasks SET completed_at=NULL,updated_at=?,version=version+1 WHERE id=?",
                         (utc_now(), task_id))
            reopened = get_existing(conn, task_id)
            record_change(conn, "task", task_id, "upsert", reopened, reopened["updated_at"])
            return reopened

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: str, expected_version: int = Query(ge=1)):
        with db.transaction() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, expected_version)
            # Detach direct children explicitly so sync devices see their parent changes.
            children = conn.execute("SELECT id FROM tasks WHERE parent_id=?", (task_id,)).fetchall()
            now = utc_now()
            for child in children:
                conn.execute(
                    "UPDATE tasks SET parent_id=NULL,updated_at=?,version=version+1 WHERE id=?",
                    (now, child["id"])
                )
                record_change(conn, "task", child["id"], "upsert",
                              get_existing(conn, child["id"]), now)
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            # Privacy removal must purge old sync payloads and cached retry responses,
            # while leaving tombstone cursor continuity to erase client copies.
            scrub_task_history(conn, task_id)
            record_change(conn, "task", task_id, "delete", None, utc_now())

    @router.get("/sync/bootstrap")
    def sync_bootstrap():
        """Consistent initial snapshot and cursor; clients must use changes after it."""
        with db.open() as conn:
            conn.execute("BEGIN")
            cursor = conn.execute("SELECT COALESCE(MAX(cursor),0) FROM change_events").fetchone()[0]
            tasks = conn.execute("SELECT * FROM tasks ORDER BY id LIMIT 5001").fetchall()
            projects = conn.execute("SELECT * FROM projects ORDER BY id LIMIT 5001").fetchall()
            if len(tasks) > 5000 or len(projects) > 5000:
                raise HTTPException(status_code=413, detail="Snapshot exceeds 5000 records; export in smaller batches")
            return {"format": "goreecloud-tasks-sync-1", "cursor": cursor,
                    "tasks": [task_dict(row) for row in tasks],
                    "projects": [dict(row) for row in projects]}

    @router.get("/sync/changes")
    def sync_changes(after: int = Query(default=0, ge=0),
                     limit: int = Query(default=100, ge=1, le=200)):
        """Monotonic append-only feed. Tombstones prevent deleted tasks reappearing."""
        with db.open() as conn:
            rows = conn.execute("""
                SELECT * FROM change_events WHERE cursor>?
                ORDER BY cursor LIMIT ?
            """, (after, limit + 1)).fetchall()
            page = rows[:limit]
            next_cursor = page[-1]["cursor"] if page else after
            return {"format": "goreecloud-tasks-sync-1", "after": after,
                    "next_cursor": next_cursor, "has_more": len(rows) > limit,
                    "changes": [
                        {"cursor": row["cursor"], "entity": row["entity"],
                         "entity_id": row["entity_id"], "operation": row["operation"],
                         "payload": json.loads(row["payload"]) if row["payload"] else None,
                         "created_at": row["created_at"]}
                        for row in page
                    ]}

    @router.get("/export.ics")
    def export_ical():
        """Authenticated VTODO file. This is an explicit export, not a public feed."""
        with db.open() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id LIMIT 5001").fetchall()
            if len(rows) > 5000:
                raise HTTPException(status_code=413, detail="Calendar export exceeds 5000 tasks")
            calendar = build_calendar([task_dict(row) for row in rows])
        return Response(
            content=calendar, media_type="text/calendar; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="goreecloud-tasks.ics"',
                     "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        )

    @router.get("/export")
    def export_data():
        with db.open() as conn:
            return {"format": "goreecloud-tasks-1",
                    "projects": [dict(row) for row in conn.execute("SELECT * FROM projects")],
                    "tasks": [task_dict(row) for row in conn.execute("SELECT * FROM tasks")]}
    app.include_router(router, dependencies=[Depends(require_token)])
    return app


# Start with: uvicorn goreecloud_tasks.app:create_app --factory
# Factory construction refuses missing/weak secrets before accepting requests.
# Do not instantiate a fallback app when credentials are absent.
