"""Read-only proposed schema-4 graph validation; no database migration or import."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from backup import BackupError, MAX_BYTES, validate as validate_legacy


def validate_proposed_graph(snapshot):
    if type(snapshot) is not dict or type(snapshot.get("schema")) is not int or snapshot["schema"] != 4:
        raise BackupError("Expected proposed schema 4")
    raw_tasks = snapshot.get("tasks")
    if type(raw_tasks) is not list:
        raise BackupError("Missing task array")
    legacy_tasks = []
    for task in raw_tasks:
        if type(task) is not dict or "parentId" not in task:
            raise BackupError("Missing parentId")
        parent = task["parentId"]
        if parent is not None and (
            type(parent) is not str or not 1 <= len(parent.encode("utf-16-le", "surrogatepass")) // 2 <= 128 or
            any(ord(ch) < 32 or ord(ch) == 127 or 0xD800 <= ord(ch) <= 0xDFFF for ch in parent)
        ):
            raise BackupError("Invalid parentId")
        legacy_tasks.append({key: value for key, value in task.items() if key != "parentId"})
    validated = validate_legacy({**snapshot, "schema": 3, "tasks": legacy_tasks})
    by_id = {task["id"]: task for task in raw_tasks}
    counts = Counter(task["projectId"] for task in raw_tasks)
    if any(n > 300 for n in counts.values()):
        raise BackupError("Project exceeds 300 active tasks including subtasks")
    depths = {}
    for task in raw_tasks:
        chain = set()
        parent_id = task["id"]
        depth = 0
        while parent_id is not None:
            if parent_id in chain:
                raise BackupError("Subtask parent cycle")
            chain.add(parent_id)
            depth += 1
            if depth > 3:
                raise BackupError("Subtask nesting exceeds three levels")
            record = by_id.get(parent_id)
            if record is None:
                raise BackupError("Missing parent task")
            if record["projectId"] != task["projectId"]:
                raise BackupError("Cross-project subtask relationship")
            parent_id = record["parentId"]
        depths[task["id"]] = depth
    return {
        **validated,
        "schema": 4,
        "tasks": [
            {**task, "parentId": by_id[task["id"]]["parentId"]}
            for task in validated["tasks"]
        ],
        "depths": depths,
    }


def parse_proposed_graph(raw):
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise BackupError("Proposed backup is too large or not bytes")
    import json
    try:
        return validate_proposed_graph(json.loads(raw.decode("utf-8")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BackupError("Invalid proposed UTF-8 JSON") from error
