"""SQLite-backed, offline-only task data for the native GTK4 GoreeCloud Tasks client."""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

PRIORITIES = (1, 2, 3, 4)
VIEWS = ("Open", "Today", "Upcoming", "Priority", "Completed", "Project")


class TaskStore:
    def __init__(self, db_path: str | Path | None = None):
        db_path_is_default = db_path is None
        if db_path is None:
            home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
            db_path = home / "goreecloud-tasks" / "tasks.sqlite3"
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if db_path_is_default:
            self.path.parent.chmod(0o700)
        if self.path.is_symlink():
            raise ValueError("Refusing symlinked task database")
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
                os.close(fd)
            except FileExistsError:
                raise ValueError("Task database was created concurrently; reopen safely")
        if not self.path.is_file():
            raise ValueError("Task database path is not a regular file")
        self.path.chmod(0o600)
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
        if not isinstance(title, str):
            raise ValueError("Task title must be text")
        title = title.strip()
        if any(0xD800 <= ord(char) <= 0xDFFF for char in title):
            raise ValueError("Task title contains invalid Unicode")
        if not 1 <= len(title) <= 240:
            raise ValueError("Task title must be 1–240 characters")
        if type(priority) is not int or priority not in PRIORITIES:
            raise ValueError("Priority must be 1–4")
        if due_date is not None and not isinstance(due_date, str):
            raise ValueError("Due date must be text or None")
        if due_date:
            try:
                parsed = datetime.strptime(due_date, "%Y-%m-%d")
                if parsed.strftime("%Y-%m-%d") != due_date:
                    raise ValueError()
            except ValueError as error:
                raise ValueError("Due date must be a valid YYYY-MM-DD date") from error
        task_id = str(uuid4())
        with self.db:
            self.db.execute(
                "INSERT INTO tasks (id,title,priority,due_date,project_id,created_at) VALUES (?,?,?,?,?,?)",
                (task_id, title, priority, due_date or None, project_id,
                 datetime.now(timezone.utc).isoformat()))
        return task_id

    def update_task(self, task_id: str, *, title: str, priority: int = 4,
                    due_date: str | None = None, project_id: str | None = None) -> bool:
        """Edit task fields in one transaction without losing completion metadata."""
        if not isinstance(title, str):
            raise ValueError("Task title must be text")
        title = title.strip()
        if any(0xD800 <= ord(char) <= 0xDFFF for char in title):
            raise ValueError("Task title contains invalid Unicode")
        if not 1 <= len(title) <= 240:
            raise ValueError("Task title must be 1–240 characters")
        if type(priority) is not int or priority not in PRIORITIES:
            raise ValueError("Priority must be 1–4")
        if due_date is not None and not isinstance(due_date, str):
            raise ValueError("Due date must be text or None")
        if due_date:
            try:
                parsed = datetime.strptime(due_date, "%Y-%m-%d")
                if parsed.strftime("%Y-%m-%d") != due_date:
                    raise ValueError()
            except ValueError as error:
                raise ValueError("Due date must be a valid YYYY-MM-DD date") from error
        if project_id is not None and not isinstance(project_id, str):
            raise ValueError("Project ID must be text or None")
        with self.db:
            result = self.db.execute(
                "UPDATE tasks SET title=?,priority=?,due_date=?,project_id=? WHERE id=?",
                (title, priority, due_date or None, project_id, task_id)
            )
        return result.rowcount == 1

    def list_tasks(self, *, include_completed: bool = False, view: str | None = None,
                   query: str = "", project_id: str | None = None,
                   today: str | None = None) -> list[dict]:
        if view is None:
            view = "Open" if not include_completed else "All"
        if view not in (*VIEWS, "All"):
            raise ValueError("Unknown task view")
        clauses, params = [], []
        if view == "Completed":
            clauses.append("completed=1")
        elif view != "All":
            clauses.append("completed=0")
        if view == "Today":
            clauses.append("due_date IS NOT NULL AND due_date<=?")
            params.append(today or date.today().isoformat())
        elif view == "Upcoming":
            clauses.append("due_date>?")
            params.append(today or date.today().isoformat())
        elif view == "Priority":
            clauses.append("priority<=2")
        elif view == "Project":
            if project_id is None:
                clauses.append("project_id IS NULL")
            else:
                clauses.append("project_id=?")
                params.append(project_id)
        if query.strip():
            # LIKE escapes user wildcards so the query is a literal substring.
            clauses.append("title LIKE ? ESCAPE '\\'")
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.append("%" + escaped + "%")
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.db.execute(
            f"SELECT * FROM tasks {where} ORDER BY completed, priority, "
            "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, created_at DESC",
            params
        ).fetchall()
        return [dict(row) for row in rows]

    def complete_task(self, task_id: str, completed: bool) -> bool:
        with self.db:
            cur = self.db.execute(
                "UPDATE tasks SET completed=?, completed_at=? WHERE id=?",
                (int(completed), datetime.now(timezone.utc).isoformat() if completed else None, task_id))
        return cur.rowcount > 0

    def rename_task(self, task_id: str, title: str) -> bool:
        if not isinstance(title, str):
            raise ValueError("Task title must be text")
        title = title.strip()
        if any(0xD800 <= ord(char) <= 0xDFFF for char in title):
            raise ValueError("Task title contains invalid Unicode")
        if not 1 <= len(title) <= 240:
            raise ValueError("Task title must be 1–240 characters")
        with self.db:
            cur = self.db.execute("UPDATE tasks SET title=? WHERE id=?", (title, task_id))
        return cur.rowcount > 0

    def delete_task(self, task_id: str) -> bool:
        with self.db:
            cur = self.db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cur.rowcount > 0

    def add_project(self, name: str) -> str:
        if not isinstance(name, str):
            raise ValueError("Project name must be text")
        name = name.strip()
        if any(0xD800 <= ord(char) <= 0xDFFF for char in name):
            raise ValueError("Project name contains invalid Unicode")
        if not 1 <= len(name) <= 100:
            raise ValueError("Project name must be 1–100 characters")
        project_id = str(uuid4())
        with self.db:
            self.db.execute("INSERT INTO projects(id,name) VALUES (?,?)", (project_id, name))
        return project_id

    def list_projects(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM projects ORDER BY name")]

    def close(self) -> None:
        self.db.close()
