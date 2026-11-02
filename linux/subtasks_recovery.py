"""Pure, preview-only proposed subtree Trash/restore. NOT wired to SQLite."""
from __future__ import annotations

from copy import deepcopy
import json
import re

from backup import _timestamp, BackupError
from subtasks_contract import validate_proposed_graph

MAX_TRASH = 1000
MAX_LOCAL_BYTES = 3 * 1024 * 1024
GROUP_ID = re.compile(r"^[a-zA-Z0-9-]{1,128}$")


def _group_id(group_id):
    if type(group_id) is not str or not GROUP_ID.fullmatch(group_id):
        raise BackupError("Invalid recovery group ID")


def _limit(workspace, trash):
    if len(trash) > MAX_TRASH or len(json.dumps(
        {"workspace": workspace, "trash": trash}, ensure_ascii=False
    ).encode("utf-8")) > MAX_LOCAL_BYTES:
        raise BackupError("Proposed local Trash capacity exceeded; no changes applied")


def plan_subtree_trash(workspace, trash, root_id, deleted_at, group_id):
    validate_proposed_graph(workspace)
    _group_id(group_id)
    if not _timestamp(deleted_at):
        raise BackupError("Invalid deletion timestamp")
    if type(trash) is not list or any(
        type(entry) is not dict or entry.get("groupId") == group_id
        for entry in trash
    ):
        raise BackupError("Recovery group already exists or Trash is invalid")
    by_id = {task["id"]: task for task in workspace["tasks"]}
    if root_id not in by_id:
        raise BackupError("Root task no longer exists")
    children = {}
    for task in workspace["tasks"]:
        if task["parentId"] is not None:
            children.setdefault(task["parentId"], []).append(task["id"])
    ids = set()
    pending = [root_id]
    while pending:
        tid = pending.pop()
        ids.add(tid)
        pending.extend(children.get(tid, []))
    if any(type(entry.get("task")) is dict and
           entry["task"].get("id") in ids for entry in trash):
        raise BackupError("Task ID conflicts with recoverable Trash")
    transferred = [task for task in workspace["tasks"] if task["id"] in ids]
    next_workspace = deepcopy({**workspace, "tasks": [
        task for task in workspace["tasks"] if task["id"] not in ids
    ]})
    next_trash = deepcopy(trash) + [
        {"task": deepcopy(task), "deletedAt": deleted_at, "groupId": group_id,
         "groupRootId": root_id, "groupSize": len(ids)}
        for task in transferred
    ]
    validate_proposed_graph(next_workspace)
    _limit(next_workspace, next_trash)
    return {"workspace": next_workspace, "trash": next_trash, "affectedIds": sorted(ids)}


def plan_subtree_restore(workspace, trash, group_id):
    validate_proposed_graph(workspace)
    _group_id(group_id)
    if type(trash) is not list:
        raise BackupError("Trash is invalid")
    group = [entry for entry in trash if type(entry) is dict and entry.get("groupId") == group_id]
    if not group:
        raise BackupError("Recovery group not found")
    first = group[0]
    if (type(first.get("groupSize")) is not int or first["groupSize"] < 1 or
            len(group) != first["groupSize"] or len(group) > MAX_TRASH or
            any(type(entry.get("task")) is not dict or
                entry.get("groupSize") != first["groupSize"] or
                entry.get("groupRootId") != first.get("groupRootId") or
                not _timestamp(entry.get("deletedAt")) or
                "parentId" not in entry["task"] for entry in group)):
        raise BackupError("Incomplete or invalid recovery group")
    ids = [entry["task"].get("id") for entry in group]
    if len(set(ids)) != len(ids) or first.get("groupRootId") not in ids:
        raise BackupError("Recovery group has duplicate or missing roots")
    # A complete recovery group must be one connected subtree of its declared
    # root. Count parity alone could otherwise hide a swapped unrelated task.
    group_ids = set(ids)
    root_id = first["groupRootId"]
    if any(entry["deletedAt"] != first["deletedAt"] for entry in group) or any(
        entry["task"]["parentId"] not in group_ids
        for entry in group if entry["task"]["id"] != root_id
    ):
        raise BackupError("Recovery group is not one intact subtree")
    parents = {entry["task"]["id"]: entry["task"]["parentId"] for entry in group}
    for tid in group_ids - {root_id}:
        seen = set()
        current = tid
        while current != root_id:
            if current in seen or current not in parents:
                raise BackupError("Recovery group contains an unrelated task or cycle")
            seen.add(current)
            current = parents[current]

    active = {task["id"] for task in workspace["tasks"]}
    if any(tid in active for tid in ids) or any(
        type(entry) is dict and entry.get("groupId") != group_id and
        type(entry.get("task")) is dict and entry["task"].get("id") in ids
        for entry in trash
    ):
        raise BackupError("Recovery ID collision")
    next_workspace = deepcopy({
        **workspace, "tasks": [*workspace["tasks"], *(e["task"] for e in group)]
    })
    validate_proposed_graph(next_workspace)
    next_trash = deepcopy([
        e for e in trash if not (type(e) is dict and e.get("groupId") == group_id)
    ])
    _limit(next_workspace, next_trash)
    return {"workspace": next_workspace, "trash": next_trash, "restoredIds": ids}
