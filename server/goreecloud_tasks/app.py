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
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
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
    """A version-1 schema, transactional mutations and explicit revisions."""

    def __init__(self, path: str):
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.open() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
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
                PRAGMA user_version=1;
            """)

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
    def add_project(data: ProjectCreate):
        now = utc_now()
        result = {"id": new_id(), "name": data.name, "created_at": now, "updated_at": now}
        with db.open() as conn:
            conn.execute("INSERT INTO projects VALUES (:id,:name,:created_at,:updated_at)", result)
        return result

    def ensure_project(conn, project_id):
        if project_id and not conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise HTTPException(status_code=422, detail="Unknown project")

    @router.get("/tasks")
    def tasks(
        status: Literal["active", "completed", "all"] = "active",
        project_id: str | None = None,
        due_before: date | None = None,
        search: str = Query(default="", max_length=120),
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
        sql += " ORDER BY (due_date IS NULL), due_date, priority, created_at DESC LIMIT 1000"
        with db.open() as conn:
            return [task_dict(r) for r in conn.execute(sql, args)]

    @router.post("/tasks", status_code=201)
    def add_task(data: TaskCreate):
        now = utc_now()
        result = dict(id=new_id(), **data.model_dump(mode="json"),
                      series_id=None, completed_at=None, created_at=now, updated_at=now, version=1)
        with db.open() as conn:
            ensure_project(conn, result["project_id"])
            conn.execute("""
                INSERT INTO tasks
                (id,title,description,project_id,due_date,priority,tags,recurrence,series_id,
                 completed_at,created_at,updated_at,version)
                VALUES (:id,:title,:description,:project_id,:due_date,:priority,:tags,:recurrence,
                        :series_id,:completed_at,:created_at,:updated_at,:version)
            """, {**result, "tags": json.dumps(result["tags"])})
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
        with db.open() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, patch.expected_version)
            if previous["completed_at"]:
                raise HTTPException(status_code=409, detail="Reopen before editing")
            edits = patch.model_dump(exclude_unset=True, exclude={"expected_version"}, mode="json")
            candidate = TaskCreate.model_validate({**{k: previous[k] for k in TaskCreate.model_fields}, **edits})
            data = candidate.model_dump(mode="json")
            ensure_project(conn, data["project_id"])
            next_version, now = previous["version"] + 1, utc_now()
            conn.execute("""
                UPDATE tasks SET title=:title,description=:description,project_id=:project_id,
                due_date=:due_date,priority=:priority,tags=:tags,recurrence=:recurrence,
                updated_at=:now,version=:version WHERE id=:id
            """, {**data, "id": task_id, "tags": json.dumps(data["tags"]),
                  "now": now, "version": next_version})
            return get_existing(conn, task_id)

    @router.post("/tasks/{task_id}/complete")
    def complete_task(task_id: str, check: VersionCheck):
        with db.open() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, check.expected_version)
            if previous["completed_at"]:
                raise HTTPException(status_code=409, detail="Task already completed")
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
                    INSERT INTO tasks VALUES (:id,:title,:description,:project_id,:due_date,
                    :priority,:tags,:recurrence,:series_id,:completed_at,:created_at,
                    :updated_at,:version)
                """, {**new_row, "tags": json.dumps(new_row["tags"])})
                next_task = new_row
            return {"completed": get_existing(conn, task_id), "next_task": next_task}

    @router.post("/tasks/{task_id}/reopen")
    def reopen_task(task_id: str, check: VersionCheck):
        with db.open() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, check.expected_version)
            if not previous["completed_at"]:
                raise HTTPException(status_code=409, detail="Task is already active")
            conn.execute("UPDATE tasks SET completed_at=NULL,updated_at=?,version=version+1 WHERE id=?",
                         (utc_now(), task_id))
            return get_existing(conn, task_id)

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: str, expected_version: int = Query(ge=1)):
        with db.open() as conn:
            previous = get_existing(conn, task_id)
            check_revision(previous, expected_version)
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))

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
