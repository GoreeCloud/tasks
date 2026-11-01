"""Offline, non-overwriting SQLite snapshots for the experimental Tasks API.

Snapshots are local, plaintext development artifacts. They are NOT encrypted
production backups, and this module never exposes an HTTP backup endpoint.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

REQUIRED_TABLES = frozenset({"tasks", "changes", "idempotency"})


class SnapshotError(ValueError):
    """A database snapshot is missing, invalid or cannot be created safely."""


def _validate_source(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SnapshotError("Source must be an existing, regular SQLite file (not a symlink)")


def _check_database(conn: sqlite3.Connection) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()
    if not integrity or integrity[0] != "ok":
        raise SnapshotError("Source SQLite integrity check failed")
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    if not REQUIRED_TABLES.issubset(tables):
        raise SnapshotError("Source does not have the expected Tasks API schema")


def snapshot_database(source: Path, destination: Path) -> int:
    """Create a validated point-in-time snapshot without replacing existing files.

    This works with a live SQLite WAL database using SQLite's online backup API.
    A temporary private file is linked into place only after verification.
    """
    source = Path(source)
    destination = Path(destination)
    _validate_source(source)
    if not destination.parent.is_dir():
        raise SnapshotError("Destination parent directory does not exist")
    if destination.exists() or destination.is_symlink():
        raise SnapshotError("Destination already exists; no overwrite permitted")
    if source.absolute() == destination.absolute():
        raise SnapshotError("Source and destination must differ")

    temp_path = None
    try:
        # mkstemp creates an exclusive, private 0600 file in the same filesystem.
        descriptor, filename = tempfile.mkstemp(
            prefix=".goreecloud-tasks-snapshot-", dir=destination.parent
        )
        temp_path = Path(filename)
        os.close(descriptor)
        source_uri = source.absolute().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(source_uri, uri=True, timeout=10)) as reader:
            _check_database(reader)
            with closing(sqlite3.connect(temp_path, timeout=10)) as writer:
                reader.backup(writer)
                _check_database(writer)
        with temp_path.open("rb") as handle:
            os.fsync(handle.fileno())
        # Atomic create-if-absent even if another process created the target.
        os.link(temp_path, destination, follow_symlinks=False)
        return destination.stat().st_size
    except (OSError, sqlite3.Error) as error:
        raise SnapshotError("Could not create a verified local SQLite snapshot") from error
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def restore_to_new_database(backup: Path, destination: Path) -> int:
    """Restore a validated snapshot to a NEW path only; never replace live data."""
    return snapshot_database(backup, destination)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Local, non-overwriting GoreeCloud Tasks API SQLite backup (development)"
    )
    parser.add_argument("operation", choices=("backup", "restore"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "backup":
            length = snapshot_database(args.source, args.destination)
        else:
            length = restore_to_new_database(args.source, args.destination)
    except SnapshotError as error:
        print(f"Snapshot rejected: {error}", file=sys.stderr)
        return 1
    print(f"Created verified local SQLite snapshot ({length} bytes).")
    print("Keep this unencrypted development artifact private; verify restoration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
