"""Experimental SQLite offline mutation outbox and remote task projection.

This file is not connected to the web, Linux or Android applications. It makes
no network requests and neither stores nor accepts authentication credentials.
Only apply server change pages after separate transport authentication.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
import re
from pathlib import Path
import sqlite3
import stat
from uuid import UUID

MAX_MUTATION_BYTES = 64 * 1024
MAX_PAGE_CHANGES = 100
MUTATION_KINDS = frozenset(("create", "update", "delete"))
CHANGE_KINDS = frozenset(("created", "updated", "deleted"))


class OutboxError(ValueError):
    """Invalid operation, unsafe data, or inconsistent local sync state."""


class StaleCursor(OutboxError):
    """Local checkpoint changed before the remote page was applied."""


def canonical_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise OutboxError("ID must be a lowercase UUID string")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise OutboxError("ID is not a UUID") from exc
    if str(parsed) != value:
        raise OutboxError("ID must be a canonical lowercase UUID")
    return value


def safe_json(value: object) -> str:
    if not isinstance(value, dict):
        raise OutboxError("JSON payload must be an object")
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
        encoded_size = len(raw.encode("utf-8"))
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise OutboxError("JSON payload is not valid UTF-8 data") from exc
    if encoded_size > MAX_MUTATION_BYTES:
        raise OutboxError("JSON payload exceeds 64 KiB")
    return raw


class OfflineOutbox:
    """Durable, per-device queue, server projection and pull checkpoint.

    No client task records are replaced: remote task snapshots are stored in
    their own table. Remote events affecting unsent local edits mark those
    edits as conflicts for later user-guided reconciliation.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if self.path.is_symlink():
            raise OutboxError("Refusing a symlinked local database")
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        if not self.path.exists():
            flags |= os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(self.path, flags, 0o600)
        except OSError as exc:
            raise OutboxError("Cannot safely open the local outbox") from exc
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OutboxError("Outbox path is not a regular file")
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        with closing(self._open()) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS mutations (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    operation TEXT NOT NULL
                        CHECK(operation IN ('create','update','delete')),
                    expected_revision INTEGER,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending'
                        CHECK(state IN ('pending','conflict','acknowledged')),
                    remote_conflict_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_outbox_state
                    ON mutations(state,id);
                CREATE TABLE IF NOT EXISTS remote_tasks (
                    task_id TEXT PRIMARY KEY,
                    snapshot_json TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    seq INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sync_cursor (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    seq INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO sync_cursor(singleton,seq) VALUES (1,0);
                CREATE TABLE IF NOT EXISTS bootstrap_state (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    applied INTEGER NOT NULL CHECK(applied IN (0,1))
                );
                INSERT OR IGNORE INTO bootstrap_state(singleton,applied) VALUES (1,0);
            """)
            db.commit()

    def _open(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def queue(self, mutation_id: str, task_id: str, operation: str,
              payload: dict, expected_revision: int | None = None) -> bool:
        """Enqueue once. Identical retry is harmless; changed reuse is rejected."""
        canonical_uuid(mutation_id)
        canonical_uuid(task_id)
        if operation not in MUTATION_KINDS:
            raise OutboxError("Unsupported mutation operation")
        if operation == "create":
            if expected_revision is not None:
                raise OutboxError("Create cannot have an expected revision")
        elif type(expected_revision) is not int or expected_revision < 1:
            raise OutboxError("Edit/delete requires a positive expected revision")
        raw = safe_json(payload)
        if operation == "delete" and payload:
            raise OutboxError("Delete operation must use an empty payload")
        if operation == "create" and not payload:
            raise OutboxError("Create needs a nonempty payload")
        with closing(self._open()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT task_id,operation,expected_revision,payload_json "
                "FROM mutations WHERE id=?", (mutation_id,)
            ).fetchone()
            if prior:
                if (prior["task_id"], prior["operation"], prior["expected_revision"],
                        prior["payload_json"]) != (task_id, operation, expected_revision, raw):
                    raise OutboxError("Mutation ID reused for different content")
                return False
            db.execute(
                "INSERT INTO mutations(id,task_id,operation,expected_revision,payload_json) "
                "VALUES (?,?,?,?,?)",
                (mutation_id, task_id, operation, expected_revision, raw)
            )
        return True

    def pending(self, limit: int = 100) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= MAX_PAGE_CHANGES:
            raise OutboxError("Pending limit must be 1 through 100")
        with closing(self._open()) as db:
            rows = db.execute(
                "SELECT * FROM mutations WHERE state='pending' ORDER BY rowid LIMIT ?",
                (limit,)
            ).fetchall()
        return [{
            "id": r["id"], "taskId": r["task_id"], "operation": r["operation"],
            "expectedRevision": r["expected_revision"],
            "payload": json.loads(r["payload_json"])
        } for r in rows]

    def acknowledge(self, mutation_id: str) -> bool:
        canonical_uuid(mutation_id)
        with closing(self._open()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM mutations WHERE id=?", (mutation_id,)).fetchone()
            if row is None:
                raise OutboxError("Unknown mutation acknowledgement")
            if row["state"] == "conflict":
                raise OutboxError("Conflict requires reconciliation, not acknowledgement")
            result = db.execute(
                "UPDATE mutations SET state='acknowledged' WHERE id=? AND state='pending'",
                (mutation_id,)
            )
            return result.rowcount == 1

    def mark_conflict(self, mutation_id: str, server_snapshot: dict) -> None:
        canonical_uuid(mutation_id)
        remote = safe_json(server_snapshot)
        with closing(self._open()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                "UPDATE mutations SET state='conflict',remote_conflict_json=? "
                "WHERE id=? AND state='pending'", (remote, mutation_id)
            )
            if result.rowcount != 1:
                raise OutboxError("Mutation missing or already finalized")

    def conflict(self, mutation_id: str) -> dict | None:
        canonical_uuid(mutation_id)
        with closing(self._open()) as db:
            row = db.execute(
                "SELECT remote_conflict_json FROM mutations "
                "WHERE id=? AND state='conflict'", (mutation_id,)
            ).fetchone()
        return json.loads(row[0]) if row and row[0] else None

    def cursor(self) -> int:
        with closing(self._open()) as db:
            return db.execute("SELECT seq FROM sync_cursor WHERE singleton=1").fetchone()[0]

    def remote_task(self, task_id: str) -> dict | None:
        canonical_uuid(task_id)
        with closing(self._open()) as db:
            row = db.execute(
                "SELECT snapshot_json FROM remote_tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def seed_bootstrap(self, bootstrap: dict) -> int:
        """Atomically seed a fresh remote projection and its matching cursor.

        Must be called once on a new outbox with no pending local edits. A
        missing or incomplete server snapshot is never silently accepted.
        """
        if not isinstance(bootstrap, dict) or type(bootstrap.get("schemaVersion")) is not int or bootstrap["schemaVersion"] != 1:
            raise OutboxError("Unsupported bootstrap schema")
        cursor = bootstrap.get("cursor")
        tasks = bootstrap.get("tasks")
        if type(cursor) is not int or not 0 <= cursor < 2**63:
            raise OutboxError("Invalid bootstrap cursor")
        if not isinstance(tasks, list) or len(tasks) > MAX_PAGE_CHANGES:
            raise OutboxError("Incomplete or oversized bootstrap snapshot")
        planned, seen = [], set()
        for task in tasks:
            raw = safe_json(task)
            task_id = canonical_uuid(task.get("id"))
            if task_id in seen:
                raise OutboxError("Duplicate task in snapshot")
            seen.add(task_id)
            revision = task.get("revision")
            if type(revision) is not int or revision < 1 or task.get("deleted") is not False:
                raise OutboxError("Invalid live task snapshot")
            planned.append((task_id, raw, revision, cursor))
        with closing(self._open()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT applied FROM bootstrap_state WHERE singleton=1").fetchone()[0]:
                raise OutboxError("Bootstrap is already applied")
            if db.execute("SELECT seq FROM sync_cursor WHERE singleton=1").fetchone()[0] != 0:
                raise OutboxError("Outbox already has a sync checkpoint")
            if db.execute("SELECT COUNT(*) FROM mutations").fetchone()[0]:
                raise OutboxError("Refusing bootstrap over local mutations")
            if db.execute("SELECT COUNT(*) FROM remote_tasks").fetchone()[0]:
                raise OutboxError("Refusing bootstrap over remote projection")
            db.executemany(
                "INSERT INTO remote_tasks(task_id,snapshot_json,revision,seq) VALUES (?,?,?,?)",
                planned
            )
            db.execute("UPDATE sync_cursor SET seq=? WHERE singleton=1", (cursor,))
            db.execute("UPDATE bootstrap_state SET applied=1 WHERE singleton=1")
        return cursor

    def apply_change_page(self, page: dict, expected_cursor: int) -> int:
        """Apply one validated single-user delta page with atomic checkpoint.

        The existing API uses contiguous single-user sequences. Future
        workspace-filtered feeds need a revised cursor contract; do not reuse
        this validator for those feeds without updating the protocol.
        """
        if type(expected_cursor) is not int or expected_cursor < 0:
            raise OutboxError("Invalid checkpoint")
        if not isinstance(page, dict) or not isinstance(page.get("changes"), list):
            raise OutboxError("Invalid change page")
        changes = page["changes"]
        if len(changes) > MAX_PAGE_CHANGES or type(page.get("hasMore")) is not bool:
            raise OutboxError("Invalid change-page length or continuation")
        if not changes and page["hasMore"]:
            raise OutboxError("Empty pages cannot have more records")
        planned = []
        seq = expected_cursor
        for change in changes:
            if not isinstance(change, dict) or type(change.get("seq")) is not int:
                raise OutboxError("Invalid change sequence")
            if change["seq"] != seq + 1:
                raise OutboxError("Change gap or duplicate")
            seq = change["seq"]
            operation = change.get("operation")
            if operation not in CHANGE_KINDS:
                raise OutboxError("Unsupported server operation")
            task = change.get("task")
            raw = safe_json(task)
            task_id = canonical_uuid(task.get("id"))
            revision = task.get("revision")
            deleted = task.get("deleted")
            if type(revision) is not int or revision < 1:
                raise OutboxError("Invalid task revision")
            if type(deleted) is not bool or (operation == "deleted") != deleted:
                raise OutboxError("Invalid deletion marker")
            mutation_id = change.get("mutationId")
            if mutation_id is not None and (not isinstance(mutation_id, str) or
                    not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", mutation_id)):
                raise OutboxError("Invalid source mutation identifier")
            planned.append((task_id, raw, revision, seq, mutation_id, operation))
        if type(page.get("cursor")) is not int or page["cursor"] != seq:
            raise OutboxError("Page cursor mismatch")
        with closing(self._open()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT seq FROM sync_cursor WHERE singleton=1").fetchone()[0]
            if current != expected_cursor:
                raise StaleCursor("Checkpoint advanced; refresh page before retry")
            for task_id, raw, revision, position, mutation_id, operation in planned:
                previous = db.execute(
                    "SELECT revision FROM remote_tasks WHERE task_id=?", (task_id,)
                ).fetchone()
                if previous and previous["revision"] >= revision:
                    raise OutboxError("Remote revision did not advance")
                db.execute(
                    "INSERT INTO remote_tasks(task_id,snapshot_json,revision,seq) "
                    "VALUES (?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET "
                    "snapshot_json=excluded.snapshot_json,revision=excluded.revision,seq=excluded.seq",
                    (task_id, raw, revision, position)
                )
                if mutation_id is not None:
                    local = db.execute(
                        "SELECT operation,expected_revision,payload_json FROM mutations "
                        "WHERE id=? AND task_id=? AND state='pending'",
                        (mutation_id, task_id)
                    ).fetchone()
                    if local:
                        expected_operation = {"created": "create", "updated": "update",
                                              "deleted": "delete"}[operation]
                        correct_revision = (revision == 1 if operation == "created" else
                                            local["expected_revision"] == revision - 1)
                        if local["operation"] != expected_operation or not correct_revision:
                            raise OutboxError("Origin mutation does not match remote revision")
                        # An authenticated event's origin key alone must never
                        # acknowledge a mutation with different task content.
                        # The queue stores canonical field values, so every
                        # requested field must agree with the event snapshot.
                        requested = json.loads(local["payload_json"])
                        observed = json.loads(raw)
                        if any(type(observed.get(field)) is not type(value) or
                               observed.get(field) != value
                               for field, value in requested.items()):
                            raise OutboxError("Origin event disagrees with queued mutation")
                        db.execute(
                            "UPDATE mutations SET state='acknowledged' "
                            "WHERE id=? AND task_id=? AND state='pending'",
                            (mutation_id, task_id)
                        )
                db.execute(
                    "UPDATE mutations SET state='conflict', remote_conflict_json=? "
                    "WHERE task_id=? AND state='pending'", (raw, task_id)
                )
            db.execute("UPDATE sync_cursor SET seq=? WHERE singleton=1", (seq,))
        return seq
