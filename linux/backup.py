"""Portable schema-1 task backups for GoreeCloud Tasks Linux.

Compatible with the browser's validated JSON snapshot. Does not silently replace
an existing local database; importing into an empty store is deliberate.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile

from store import TaskStore

MAX_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 10_000
ID_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,128}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,9}))?"
    r"(?P<zone>Z|(?P<sign>[+-])(?P<offset_hour>\d{2}):(?P<offset_minute>\d{2}))$"
)


class BackupError(ValueError):
    """A snapshot is invalid or cannot be safely used."""


def _date(value):
    if value == "":
        return True
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _timestamp(value):
    """Accept the strict ISO-8601 subset used by the Android backup reader."""
    if not isinstance(value, str) or len(value) > 40:
        return False
    fields = TIME_RE.fullmatch(value)
    if fields is None or not _date(fields["date"]):
        return False
    if (int(fields["hour"]) > 23 or int(fields["minute"]) > 59
            or int(fields["second"]) > 59):
        return False
    if fields["sign"]:
        hours = int(fields["offset_hour"])
        minutes = int(fields["offset_minute"])
        if hours > 18 or minutes > 59 or (hours == 18 and minutes != 0):
            return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # The Android portable parser requires a positive epoch millisecond.
        return parsed.tzinfo is not None and int(parsed.timestamp() * 1000) > 0
    except (ValueError, OverflowError, OSError):
        return False


def _object(value):
    return type(value) is dict


def _scalar(value):
    return isinstance(value, str) and all(
        not 0xD800 <= ord(character) <= 0xDFFF for character in value
    )


def validate(data):
    if not _object(data) or type(data.get("schema")) is not int or data["schema"] not in (1, 2):
        raise BackupError("Unsupported backup version (expected schema 1 or 2)")
    if not isinstance(data.get("projects"), list) or not isinstance(data.get("tasks"), list):
        raise BackupError("Backup must contain tasks and projects arrays")
    if len(data["projects"]) > MAX_RECORDS or len(data["tasks"]) > MAX_RECORDS:
        raise BackupError("Backup contains too many records")
    projects, tasks = [], []
    ids = set()
    for project in data["projects"]:
        if not _object(project):
            raise BackupError("Invalid project")
        pid, name = project.get("id"), project.get("name")
        if not _scalar(pid) or not ID_RE.fullmatch(pid) or pid in ids:
            raise BackupError("Invalid or duplicate project ID")
        if not _scalar(name) or not 1 <= len(name.strip()) <= 100:
            raise BackupError("Invalid project name")
        ids.add(pid)
        projects.append({"id": pid, "name": name.strip()})
    task_ids = set()
    for task in data["tasks"]:
        if not _object(task):
            raise BackupError("Invalid task")
        tid = task.get("id")
        title = task.get("title")
        priority = task.get("priority")
        due = task.get("due")
        completed = task.get("completed")
        created = task.get("createdAt")
        completed_at = task.get("completedAt")
        project_id = task.get("projectId")
        if (not _scalar(tid) or not ID_RE.fullmatch(tid)
                or tid in task_ids):
            raise BackupError("Invalid or duplicate task ID")
        if not _scalar(title) or not 1 <= len(title.strip()) <= 240:
            raise BackupError("Invalid task title")
        if type(priority) is not int or not 1 <= priority <= 4:
            raise BackupError("Invalid task priority")
        if not _date(due):
            raise BackupError("Invalid task due date")
        if type(completed) is not bool or not _timestamp(created):
            raise BackupError("Invalid task completion or creation timestamp")
        if (completed_at is not None and not _timestamp(completed_at)) or completed != (completed_at is not None):
            raise BackupError("Inconsistent completion metadata")
        if project_id is not None and (not _scalar(project_id) or project_id not in ids):
            raise BackupError("Task references a missing project")
        if data["schema"] == 1 and "description" in task:
            raise BackupError("Descriptions require schema 2; backup cannot lose notes")
        description = task.get("description") if data["schema"] == 2 else None
        if data["schema"] == 2 and (not _scalar(description) or
                                    len(description.encode("utf-16-le")) // 2 > 2000):
            raise BackupError("Invalid task description")
        task_ids.add(tid)
        tasks.append({
            "id": tid, "title": title.strip(), "projectId": project_id,
            "due": due, "priority": priority, "completed": completed,
            "createdAt": created, "completedAt": completed_at,
            **({"description": description} if data["schema"] == 2 else {})
        })
    return {"schema": data["schema"], "projects": projects, "tasks": tasks}


def serialized(data):
    raw = json.dumps(validate(data), ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise BackupError("Backup exceeds 2 MiB")
    return raw


def read_backup(path: Path):
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise BackupError("Backup exceeds 2 MiB")
    try:
        return validate(json.loads(raw.decode("utf-8")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BackupError("Invalid UTF-8 JSON backup") from error


def export_data(store: TaskStore):
    all_tasks = store.list_tasks(include_completed=True)
    version = 2 if any(row["description"] for row in all_tasks) else 1
    return validate({
        "schema": version,
        "projects": store.list_projects(),
        "tasks": [{
            "id": row["id"], "title": row["title"],
            **({"description": row["description"]} if version == 2 else {}),
            "projectId": row["project_id"], "due": row["due_date"] or "",
            "priority": row["priority"], "completed": bool(row["completed"]),
            "createdAt": row["created_at"], "completedAt": row["completed_at"]
        } for row in all_tasks]
    })


def export_file(store: TaskStore, path: Path):
    """Atomically create a backup; fail if the destination already exists."""
    raw = serialized(export_data(store))
    path = Path(path)
    if path.is_symlink() or path.exists():
        raise BackupError("Destination already exists; will not overwrite")
    if not path.parent.is_dir():
        raise BackupError("Destination directory does not exist")
    file_descriptor, temp_name = tempfile.mkstemp(prefix=".goreecloud-tasks-", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists() or path.is_symlink():
            raise BackupError("Destination appeared while exporting")
        # Hard link avoids clobbering an output created by another process.
        os.link(temp_name, path, follow_symlinks=False)
    finally:
        os.unlink(temp_name)
    return len(raw)


def import_data(store: TaskStore, data):
    """Load schema-1 into an empty database in one transaction; never replace."""
    validated = validate(data)
    with store.db:
        if (store.db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
                or store.db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
                or store.db.execute("SELECT COUNT(*) FROM deleted_tasks").fetchone()[0]):
            raise BackupError(
                "Destination database is not empty (including local Trash); "
                "existing work is preserved"
            )
        for project in validated["projects"]:
            store.db.execute("INSERT INTO projects(id,name) VALUES (?,?)", (project["id"], project["name"]))
        for task in validated["tasks"]:
            store.db.execute(
                "INSERT INTO tasks(id,title,priority,due_date,project_id,completed,created_at,completed_at,description) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (task["id"], task["title"], task["priority"], task["due"] or None,
                 task["projectId"], int(task["completed"]), task["createdAt"], task["completedAt"],
                 task.get("description", ""))
            )
    return len(validated["tasks"]), len(validated["projects"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="GoreeCloud Tasks portable JSON backups (development)")
    parser.add_argument("--database", type=Path, help="SQLite task database path; default is XDG local tasks store")
    action = parser.add_subparsers(dest="action", required=True)
    for name, help_text in (
        ("export", "Write a new JSON file, without overwriting"),
        ("import", "Restore into an empty database, never overwriting")
    ):
        action.add_parser(name, help=help_text).add_argument(
            "--file", type=Path, required=True, help="JSON backup file"
        )
    args = parser.parse_args(argv)
    if args.action == "export":
        default_data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
        source_path = args.database or default_data_home / "goreecloud-tasks" / "tasks.sqlite3"
        if not source_path.is_file():
            print("Backup failed: source SQLite database does not exist", file=sys.stderr)
            return 1
    store = TaskStore(args.database)
    try:
        if args.action == "export":
            count = export_file(store, args.file)
            print(f"Exported {count} bytes to {args.file}")
        else:
            counts = import_data(store, read_backup(args.file))
            print(f"Imported {counts[0]} tasks and {counts[1]} projects into the empty local store")
    except (BackupError, sqlite3.Error, OSError) as error:
        print(f"Backup failed: {error}", file=sys.stderr)
        return 1
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
