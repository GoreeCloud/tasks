"""Private explicit CSV task export, bounded and spreadsheet-formula hardened.

This is a human-readable convenience export, NOT a lossless server backup or
an automatic import/migration. JSON export retains original values/metadata.
"""
from __future__ import annotations

import csv
import io

from fastapi import HTTPException

MAX_EXPORT_ROWS = 5000
MAX_EXPORT_BYTES = 10_000_000
COLUMNS = (
    "id", "title", "description", "due_date", "priority", "tags",
    "recurrence", "parent_id", "project_id", "project_name",
    "completed_at", "series_id", "version", "created_at", "updated_at",
)


def spreadsheet_text(value: object) -> str:
    """Prevent leading spreadsheet formula execution, including whitespace."""
    if value is None:
        return ""
    text = str(value)
    leading = " \t\r\n\v\f\ufeff\u200b\u2060"
    first = text.lstrip(leading)
    if text.startswith(("\t", "\r", "\n", "\ufeff", "\u200b", "\u2060")) or (
        first and first[0] in "=+-@"
    ):
        return "'" + text
    return text


def build_task_csv(tasks: list[dict]) -> str:
    if len(tasks) > MAX_EXPORT_ROWS:
        raise HTTPException(status_code=413, detail="Task CSV export exceeds 5000 tasks")
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for item in tasks:
        tags = item.get("tags") or []
        if not isinstance(tags, list):
            raise ValueError("Invalid task tag structure")
        values = {
            **item, "tags": "|".join(str(tag) for tag in tags)
        }
        writer.writerow([spreadsheet_text(values.get(name)) for name in COLUMNS])
        # Early bounded allocation; final check covers multi-byte UTF-8 data.
        if output.tell() > MAX_EXPORT_BYTES:
            raise HTTPException(status_code=413, detail="Task CSV export exceeds 10 MB")
    payload = output.getvalue()
    if len(payload.encode("utf-8")) > MAX_EXPORT_BYTES:
        raise HTTPException(status_code=413, detail="Task CSV export exceeds 10 MB")
    return payload
