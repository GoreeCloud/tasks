"""Operator-owned online SQLite backup and integrity verification.

Uses sqlite3.Connection.backup to preserve a consistent snapshot while the
service is running in WAL mode. Never overwrites a preexisting destination.
No credentials, task content or host paths are printed by default.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def verify(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Database must be an existing regular, non-symlinked file")
    source = sqlite3.connect("file:" + path.resolve().as_posix() + "?mode=ro", uri=True)
    try:
        result = source.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ValueError("Database integrity check failed")
        invalid = source.execute("PRAGMA foreign_key_check").fetchone()
        if invalid:
            raise ValueError("Database foreign key validation failed")
    finally:
        source.close()


def backup(source_file: Path, destination_file: Path) -> None:
    verify(source_file)
    if destination_file.exists() or destination_file.is_symlink():
        raise FileExistsError("Backup target exists; no overwrite permitted")
    if not destination_file.parent.is_dir():
        raise ValueError("Backup parent directory does not exist")
    if source_file.resolve() == destination_file.resolve():
        raise ValueError("Source and destination must differ")
    destination_file.parent.mkdir(parents=True, exist_ok=True)
    # Reserve target exclusively. Do not allow symlinks, races or overwrites.
    fd = os.open(str(destination_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect("file:" + source_file.resolve().as_posix() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(str(destination_file)) as dest:
                src.backup(dest, pages=100, sleep=0.01)
        os.chmod(destination_file, 0o600)
        verify(destination_file)
    except Exception:
        destination_file.unlink(missing_ok=True)
        raise


def verify_tasks_schema(path: Path) -> dict[str,int]:
    """Validate the expected Tasks v4 tables and count private records only."""
    verify(path)
    required = (
        "projects", "tasks", "change_events", "request_receipts",
        "habits", "habit_checkins"
    )
    with sqlite3.connect(
        "file:" + path.resolve().as_posix() + "?mode=ro", uri=True
    ) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version != 4:
            raise ValueError("Restore drill requires a GoreeCloud Tasks schema-v4 backup")
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not set(required).issubset(tables):
            raise ValueError("Restore drill backup is missing required Tasks tables")
        counts = {
            name: conn.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0]
            for name in required
        }
        counts["last_cursor"] = conn.execute(
            "SELECT COALESCE(MAX(cursor),0) FROM change_events"
        ).fetchone()[0]
        return counts


def restore_drill(backup_file: Path, new_database: Path) -> dict[str,int]:
    """Restore ONLY into a new destination. Never replace the running database.

    The source snapshot must pass SQLite integrity/FK checks and the schema-v4
    contract. Compare per-table counts and highest feed cursor after an
    exclusive, owner-only new-file creation. Roll back a malformed copy.
    """
    expected = verify_tasks_schema(backup_file)
    created = False
    try:
        backup(backup_file, new_database)
        created = True
        restored = verify_tasks_schema(new_database)
        if restored != expected:
            raise ValueError("Restored database counts or cursor do not match the backup")
        return restored
    except Exception:
        # Only remove a new file after a confirmed successful exclusive
        # creation by backup(); never unlink an existing user destination.
        if created:
            new_database.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GoreeCloud Tasks SQLite online backup and verification")
    sub = parser.add_subparsers(dest="command", required=True)
    verify_command = sub.add_parser("verify", help="Read-only integrity and foreign key check")
    verify_command.add_argument("--database", type=Path, required=True)
    backup_command = sub.add_parser("backup", help="Create a new online snapshot without overwriting")
    backup_command.add_argument("--database", type=Path, required=True)
    backup_command.add_argument("--output", type=Path, required=True)
    drill_command = sub.add_parser(
        "restore-drill",
        help="Restore a verified schema-v4 backup to a NEW destination (never overwrites)"
    )
    drill_command.add_argument("--backup", type=Path, required=True)
    drill_command.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    try:
        if options.command == "verify":
            verify(options.database)
        elif options.command == "backup":
            backup(options.database, options.output)
        else:
            restore_drill(options.backup, options.output)
        labels = {"verify": "integrity verified", "backup": "backup verified",
                  "restore-drill": "isolated restore drill verified"}
        print("GoreeCloud Tasks database " + labels[options.command])
        return 0
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        # Avoid echoing paths and credentials from the caller's environment.
        print("GoreeCloud Tasks database operation failed: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
