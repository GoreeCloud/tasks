"""Read-only legacy 1-3 → proposed v4 roots. Never writes a task database."""
from __future__ import annotations

import json

from backup import BackupError, MAX_BYTES, validate
from subtasks_contract import validate_proposed_graph


def preview_legacy_as_roots(source):
    legacy = validate(source)
    candidate = {
        "schema": 4,
        "projects": legacy["projects"],
        "tasks": [{
            **task,
            **({"description": ""} if legacy["schema"] < 2 else {}),
            **({"labels": []} if legacy["schema"] < 3 else {}),
            "parentId": None,
        } for task in legacy["tasks"]],
    }
    if len(json.dumps(candidate, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        raise BackupError("Projected schema-4 backup is too large")
    normalized = validate_proposed_graph(candidate)
    return {k: normalized[k] for k in ("schema", "projects", "tasks")}
