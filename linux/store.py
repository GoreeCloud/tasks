"""SQLite-backed, offline-only task data for the native GTK4 GoreeCloud Tasks client."""
from __future__ import annotations

import os
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

PRIORITIES = (1, 2, 3, 4)
VIEWS = ("Open", "Today", "Tomorrow", "Next 7 days", "Overdue", "Upcoming", "Priority", "Completed", "Project")


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
            -- Additive migration: deleted rows remain local and recoverable.
            -- The standalone schema-1 backup intentionally exports active tasks only.
            CREATE TABLE IF NOT EXISTS deleted_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                priority INTEGER NOT NULL,
                due_date TEXT,
                project_id TEXT,
                completed INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                deleted_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_deleted_tasks_when
                ON deleted_tasks(deleted_at DESC);
        """)
        # Additive, idempotent local migration. No existing task or Trash row is rewritten.
        for table in ("tasks", "deleted_tasks"):
            columns = {row[1] for row in self.db.execute(f"PRAGMA table_info({table})")}
            if "description" not in columns:
                self.db.execute(f"ALTER TABLE {table} ADD COLUMN description TEXT NOT NULL DEFAULT ''")
            if "labels_json" not in columns:
                self.db.execute(f"ALTER TABLE {table} ADD COLUMN labels_json TEXT NOT NULL DEFAULT '[]'")
        self.db.commit()

    @staticmethod
    def checked_description(text):
        if (type(text) is not str or len(text.encode("utf-16-le", "surrogatepass")) // 2 > 2000 or
                any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)):
            raise ValueError("Description must be valid Unicode text, at most 2000 characters")
        return text

    @staticmethod
    def checked_labels(labels):
        if type(labels) is not list or len(labels) > 8:
            raise ValueError("A task supports up to 8 labels")
        seen = set()
        for label in labels:
            if (type(label) is not str or not label or label != label.strip() or
                    len(label.encode("utf-16-le", "surrogatepass")) // 2 > 32 or
                    any(ord(ch) < 32 or ord(ch) == 127 or
                        0xD800 <= ord(ch) <= 0xDFFF or ch == "," for ch in label) or
                    label in seen):
                raise ValueError("Labels must be unique 1–32 character text without commas or controls")
            seen.add(label)
        return labels[:]

    @classmethod
    def parse_labels(cls, raw):
        if type(raw) is not str:
            raise ValueError("Labels must be text")
        return cls.checked_labels([part.strip() for part in raw.split(",")] if raw.strip() else [])

    def add_task(self, title: str, *, priority: int = 4,
                 due_date: str | None = None, project_id: str | None = None,
                 description: str = "", labels: list[str] | None = None) -> str:
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
        description = self.checked_description(description)
        labels_json = json.dumps(self.checked_labels(labels if labels is not None else []), ensure_ascii=False)
        task_id = str(uuid4())
        with self.db:
            self.db.execute(
                "INSERT INTO tasks (id,title,priority,due_date,project_id,created_at,description,labels_json) VALUES (?,?,?,?,?,?,?,?)",
                (task_id, title, priority, due_date or None, project_id,
                 datetime.now(timezone.utc).isoformat(), description, labels_json))
        return task_id

    def duplicate_task(self, task_id: str) -> str:
        """Atomically copy active task fields with a fresh ID and open history."""
        if type(task_id) is not str or not task_id:
            raise ValueError("Task ID must be a nonempty string")
        copied_id = str(uuid4())
        with self.db:
            result = self.db.execute(
                "INSERT INTO tasks "
                "(id,title,priority,due_date,project_id,completed,created_at,completed_at,description,labels_json) "
                "SELECT ?,title,priority,due_date,project_id,0,?,NULL,description,labels_json "
                "FROM tasks WHERE id=?",
                (copied_id, datetime.now(timezone.utc).isoformat(), task_id)
            )
            if result.rowcount != 1:
                raise ValueError("Task no longer exists")
        return copied_id

    def update_task(self, task_id: str, *, title: str, priority: int = 4,
                    due_date: str | None = None, project_id: str | None = None,
                    description: str | None = None,
                    labels: list[str] | None = None) -> bool:
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
        if description is not None:
            self.checked_description(description)
        labels_json = json.dumps(self.checked_labels(labels), ensure_ascii=False) if labels is not None else None
        with self.db:
            if description is None and labels_json is None:
                result = self.db.execute(
                    "UPDATE tasks SET title=?,priority=?,due_date=?,project_id=? WHERE id=?",
                    (title, priority, due_date or None, project_id, task_id))
            else:
                fields = ["title=?", "priority=?", "due_date=?", "project_id=?"]
                params = [title, priority, due_date or None, project_id]
                if description is not None:
                    fields.append("description=?")
                    params.append(description)
                if labels_json is not None:
                    fields.append("labels_json=?")
                    params.append(labels_json)
                result = self.db.execute(
                    "UPDATE tasks SET " + ",".join(fields) + " WHERE id=?",
                    params + [task_id])
        return result.rowcount == 1

    def list_tasks(self, *, include_completed: bool = False, view: str | None = None,
                   query: str = "", project_id: str | None = None,
                   today: str | None = None, priority_filter: int | None = None,
                   sort_by: str = "Smart", label_filter: str | None = None) -> list[dict]:
        if view is None:
            view = "Open" if not include_completed else "All"
        if view not in (*VIEWS, "All"):
            raise ValueError("Unknown task view")
        order_options = {
            "Smart": "completed, priority, CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, created_at DESC",
            "Due date": "completed, CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, priority, created_at DESC",
            "Title": "completed, title COLLATE NOCASE, priority, created_at DESC",
        }
        if sort_by not in order_options:
            raise ValueError("Unknown task sorting mode")
        if priority_filter is not None and (type(priority_filter) is not int or priority_filter not in PRIORITIES):
            raise ValueError("Priority filter must be P1–P4 or All")
        clauses, params = [], []
        if priority_filter is not None:
            clauses.append("priority=?")
            params.append(priority_filter)
        if view == "Completed":
            clauses.append("completed=1")
        elif view != "All":
            clauses.append("completed=0")
        if view == "Today":
            clauses.append("due_date IS NOT NULL AND due_date<=?")
            params.append(today or date.today().isoformat())
        elif view == "Tomorrow":
            current = date.fromisoformat(today) if today is not None else date.today()
            if today is not None and current.isoformat() != today:
                raise ValueError("Today must be YYYY-MM-DD")
            clauses.append("due_date=?")
            params.append((current + timedelta(days=1)).isoformat())
        elif view == "Overdue":
            clauses.append("due_date IS NOT NULL AND due_date<?")
            params.append(today or date.today().isoformat())
        elif view == "Next 7 days":
            current = date.fromisoformat(today) if today is not None else date.today()
            if today is not None and current.isoformat() != today:
                raise ValueError("Today must be YYYY-MM-DD")
            clauses.append("due_date IS NOT NULL AND due_date>=? AND due_date<=?")
            params.extend((current.isoformat(), (current + timedelta(days=6)).isoformat()))
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
            clauses.append("(title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')")
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params.extend(("%" + escaped + "%",) * 2)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        if label_filter is not None:
            self.checked_labels([label_filter])
        rows = self.db.execute(
            f"SELECT * FROM tasks {where} ORDER BY {order_options[sort_by]}", params
        ).fetchall()
        return [dict(row) for row in rows if label_filter is None or
                label_filter in self.checked_labels(json.loads(row["labels_json"]))]

    def complete_task(self, task_id: str, completed: bool) -> bool:
        """Change completion once; redundant toggles preserve the original date."""
        if type(completed) is not bool:
            raise ValueError("Task completion state must be boolean")
        flag = int(completed)
        with self.db:
            cur = self.db.execute(
                "UPDATE tasks SET completed=?, completed_at=? "
                "WHERE id=? AND completed<>?",
                (flag, datetime.now(timezone.utc).isoformat() if completed else None,
                 task_id, flag))
        return cur.rowcount > 0

    def bulk_edit_tasks(self, ids: list[str], action: str, value=None) -> int:
        """Apply one validated action to at most 200 task IDs in a single transaction.

        Unknown/stale IDs, invalid values and Trash collisions roll back all rows.
        Completion timestamps are preserved on redundant completion requests.
        """
        if (type(ids) is not list or not 1 <= len(ids) <= 200 or
                any(type(item) is not str or not item for item in ids) or
                len(set(ids)) != len(ids)):
            raise ValueError("Select 1–200 unique task IDs")
        if action not in ("complete", "reopen", "priority", "project", "trash"):
            raise ValueError("Unsupported bulk action")
        if action == "priority":
            if type(value) is not int or value not in PRIORITIES:
                raise ValueError("Priority must be P1–P4")
        elif action == "project":
            if value is not None and (type(value) is not str or not value):
                raise ValueError("Project ID must be valid or Inbox")
        elif value is not None:
            raise ValueError("Unexpected bulk action value")

        with self.db:
            for task_id in ids:
                if self.db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
                    raise ValueError("A selected task no longer exists")
            if action == "project" and value is not None:
                if self.db.execute("SELECT 1 FROM projects WHERE id=?", (value,)).fetchone() is None:
                    raise ValueError("The selected project no longer exists")
            when = datetime.now(timezone.utc).isoformat()
            for task_id in ids:
                if action in ("complete", "reopen"):
                    state = int(action == "complete")
                    self.db.execute(
                        "UPDATE tasks SET completed=?,completed_at=? WHERE id=? AND completed<>?",
                        (state, when if state else None, task_id, state)
                    )
                elif action == "priority":
                    self.db.execute("UPDATE tasks SET priority=? WHERE id=?", (value, task_id))
                elif action == "project":
                    self.db.execute("UPDATE tasks SET project_id=? WHERE id=?", (value, task_id))
                else:
                    self.db.execute(
                        "INSERT INTO deleted_tasks "
                        "(id,title,priority,due_date,project_id,completed,created_at,completed_at,description,labels_json,deleted_at) "
                        "SELECT id,title,priority,due_date,project_id,completed,created_at,completed_at,description,labels_json,? "
                        "FROM tasks WHERE id=?",
                        (when, task_id)
                    )
                    if self.db.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount != 1:
                        raise sqlite3.IntegrityError("Task changed during bulk deletion")
        return len(ids)

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
        """Move a task to local durable Trash in one SQLite transaction."""
        with self.db:
            current = self.db.execute(
                "SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
            if current is None:
                return False
            # Never overwrite an older trashed row if the ID was later
            # reintroduced via an import; a collision rolls back safely.
            self.db.execute(
                "INSERT INTO deleted_tasks "
                "(id,title,priority,due_date,project_id,completed,created_at,completed_at,description,labels_json,deleted_at) "
                "SELECT id,title,priority,due_date,project_id,completed,created_at,completed_at,description,labels_json,? "
                "FROM tasks WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), task_id)
            )
            cur = self.db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            if cur.rowcount != 1:
                raise sqlite3.IntegrityError("Task changed during deletion")
        return True

    def list_deleted_tasks(self, *, query: str = "", label_filter: str | None = None) -> list[dict]:
        """Deleted rows are local-only and excluded from portable backups."""
        if not isinstance(query, str):
            raise ValueError("Search must be text")
        params = []
        where = ""
        if query.strip():
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where = "WHERE (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')"
            params.extend(("%" + escaped + "%",) * 2)
        if label_filter is not None:
            self.checked_labels([label_filter])
        rows = self.db.execute(
            "SELECT * FROM deleted_tasks " + where +
            " ORDER BY deleted_at DESC, id", params
        ).fetchall()
        return [dict(row) for row in rows if label_filter is None or
                label_filter in self.checked_labels(json.loads(row["labels_json"]))]

    def restore_deleted_task(self, task_id: str) -> bool:
        """Recreate the original task atomically; preserve timestamps and ID."""
        with self.db:
            row = self.db.execute(
                "SELECT * FROM deleted_tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                return False
            if (row["project_id"] is not None and
                    self.db.execute("SELECT 1 FROM projects WHERE id=?",
                                    (row["project_id"],)).fetchone() is None):
                raise ValueError("Original project no longer exists; task not restored")
            # An ID collision raises and rolls back, leaving Trash untouched.
            self.db.execute(
                "INSERT INTO tasks "
                "(id,title,priority,due_date,project_id,completed,created_at,completed_at,description,labels_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                tuple(row[field] for field in
                      ("id", "title", "priority", "due_date", "project_id",
                       "completed", "created_at", "completed_at", "description", "labels_json"))
            )
            removed = self.db.execute(
                "DELETE FROM deleted_tasks WHERE id=?", (task_id,))
            if removed.rowcount != 1:
                raise sqlite3.IntegrityError("Trash changed during restoration")
        return True

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
