"""IN-MEMORY ONLY test reference for atomic v4 subtree Trash and restore.

No production tables, file-backed databases, migration or UI uses this class.
"""
from __future__ import annotations

import json
import sqlite3

from backup import BackupError
from subtasks_contract import validate_proposed_graph
from subtasks_recovery import plan_subtree_trash, plan_subtree_restore


class InMemorySubtreeReference:
    def __init__(self, connection: sqlite3.Connection):
        # Never create preview tables in a user's persisted database.
        files = list(connection.execute("PRAGMA database_list"))
        if len(files) != 1 or files[0][1] != "main" or files[0][2] != "":
            raise ValueError("Subtree transaction reference is memory-only")
        self.db = connection
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS proposed_meta (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proposed_tasks (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proposed_trash (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                deleted_at TEXT NOT NULL, group_id TEXT NOT NULL,
                group_root_id TEXT NOT NULL, group_size INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_proposed_group ON proposed_trash(group_id);
        """)

    @staticmethod
    def _json(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def seed(self, snapshot):
        validate_proposed_graph(snapshot)
        if self.db.execute("SELECT 1 FROM proposed_meta LIMIT 1").fetchone():
            raise ValueError("Reference workspace already seeded")
        with self.db:
            self.db.execute("INSERT INTO proposed_meta VALUES ('projects',?)",
                            (self._json(snapshot["projects"]),))
            for task in snapshot["tasks"]:
                self.db.execute("INSERT INTO proposed_tasks VALUES (?,?)",
                                (task["id"], self._json(task)))

    def workspace(self):
        row = self.db.execute("SELECT value FROM proposed_meta WHERE key='projects'").fetchone()
        if row is None:
            raise ValueError("Reference not seeded")
        tasks = [json.loads(row[0]) for row in
                 self.db.execute("SELECT payload FROM proposed_tasks ORDER BY rowid")]
        return {"schema": 4, "projects": json.loads(row[0]), "tasks": tasks}

    def trash(self):
        result = []
        for payload, deleted, group, root, size in self.db.execute(
            "SELECT payload,deleted_at,group_id,group_root_id,group_size "
            "FROM proposed_trash ORDER BY rowid"
        ):
            result.append({"task": json.loads(payload), "deletedAt": deleted,
                           "groupId": group, "groupRootId": root, "groupSize": size})
        return result

    def _transaction(self, operation):
        if self.db.in_transaction:
            raise ValueError("Reference operation requires a new transaction")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            output = operation()
            self.db.commit()
            return output
        except BaseException:
            self.db.rollback()
            raise

    def delete_subtree(self, root_id, deleted_at, group_id):
        def apply():
            plan = plan_subtree_trash(self.workspace(), self.trash(),
                                      root_id, deleted_at, group_id)
            for entry in plan["trash"]:
                if entry["groupId"] != group_id:
                    continue
                self.db.execute(
                    "INSERT INTO proposed_trash "
                    "(id,payload,deleted_at,group_id,group_root_id,group_size) "
                    "VALUES (?,?,?,?,?,?)",
                    (entry["task"]["id"], self._json(entry["task"]),
                     entry["deletedAt"], entry["groupId"],
                     entry["groupRootId"], entry["groupSize"])
                )
                result = self.db.execute("DELETE FROM proposed_tasks WHERE id=?",
                                         (entry["task"]["id"],))
                if result.rowcount != 1:
                    raise BackupError("Task changed during preview deletion")
            validate_proposed_graph(self.workspace())
            return plan["affectedIds"]
        return self._transaction(apply)

    def restore_group(self, group_id):
        def apply():
            plan = plan_subtree_restore(self.workspace(), self.trash(), group_id)
            for entry in self.trash():
                if entry["groupId"] != group_id:
                    continue
                self.db.execute("INSERT INTO proposed_tasks VALUES (?,?)",
                                (entry["task"]["id"], self._json(entry["task"])))
                result = self.db.execute("DELETE FROM proposed_trash WHERE id=?",
                                         (entry["task"]["id"],))
                if result.rowcount != 1:
                    raise BackupError("Trash changed during preview restoration")
            validate_proposed_graph(self.workspace())
            return plan["restoredIds"]
        return self._transaction(apply)
