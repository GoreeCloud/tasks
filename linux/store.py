"""Local, single-device SQLite task store for the native GTK application.

No cross-device synchronization or multi-user access is claimed in this foundation.
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PRIORITIES = (1, 2, 3, 4)


class TaskStore:
    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
            db_path = data_home / "goreecloud-tasks" / "tasks.sqlite3"
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL CHECK(length(title) <= 240 AND length(title) > 0),
                priority INTEGER NOT NULL DEFAULT 4 CHECK(priority BETWEEN 1 AND 4),
                due_date TEXT,
                project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_sort ON tasks(completed, priority, due_date);
        """)
        self.db.commit()

    def add_task(self, title: str, *, priority: int = 4,
                 due_date: str | None = None, project_id: str | None = None) -> str:
        title = title.strip()
        if not 1 <= len(title) <= 240:
            raise ValueError("Task title must be 1–240 characters")
        if priority not in PRIORITIES:
            raise ValueError("Priority must be 1–4")
        if due_date:
            if datetime.strptime(due_date, "%Y-%m-%d").strftime("%Y-%m-%d") != due_date:
                raise ValueError("Due date must be ISO YYYY-MM-DD")
        task_id = str(uuid4())
        with self.db:
            self.db.execute(
                "INSERT INTO tasks (id,title,priority,due_date,project_id,created_at) VALUES (?,?,?,?,?,?)",
                (task_id, title, priority, due_date, project_id,
                 datetime.now(timezone.utc).isoformat()))
        return task_id

    def list_tasks(self, *, include_completed: bool = False) -> list[dict]:
        condition = "" if include_completed else "WHERE completed=0"
        rows = self.db.execute(
            f"SELECT * FROM tasks {condition} ORDER BY completed, priority, "
            "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def complete_task(self, task_id: str, completed: bool) -> bool:
        with self.db:
            cur = self.db.execute(
                "UPDATE tasks SET completed=?, completed_at=? WHERE id=?",
                (int(completed), datetime.now(timezone.utc).isoformat() if completed else None, task_id))
        return cur.rowcount > 0

    def delete_task(self, task_id: str) -> bool:
        with self.db:
            cur = self.db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cur.rowcount > 0

    def add_project(self, name: str) -> str:
        name = name.strip()
        if not 1 <= len(name) <= 100:
            raise ValueError("Project name must be 1–100 characters")
        project_id = str(uuid4())
        with self.db:
            self.db.execute("INSERT INTO projects(id,name) VALUES (?,?)", (project_id, name))
        return project_id

    def list_projects(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM projects ORDER BY name")]

    def close(self) -> None:
        self.db.close()
