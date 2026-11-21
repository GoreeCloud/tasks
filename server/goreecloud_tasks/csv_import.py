"""Strict, bounded preview-first task migration from generic or Todoist CSV.

No network access, no native providers, no automatic file persistence. The
parser rejects malformed, unsupported dates rather than losing scheduling
data. Commit routes use the Store's BEGIN IMMEDIATE transaction and a required
idempotency key.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field


MAX_CSV_CHARACTERS = 500_000
MAX_TASKS = 200
MAX_INPUT_ROWS = 500


class CsvSource(BaseModel):
    format: Literal["generic", "todoist"]
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARACTERS)
    project_id: str | None = None
    flatten_hierarchy: bool = False


class CsvImport(CsvSource):
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


def checksum(source: CsvSource) -> str:
    """Bind a commit to the exact previously previewed CSV and options."""
    serialized = json.dumps(source.model_dump(exclude={"checksum"}), sort_keys=True,
                            ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _parse_date(value: str, row: int) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        valid = date.fromisoformat(raw)
        if valid.isoformat() != raw:
            raise ValueError()
        return raw
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"CSV row {row}: date must use YYYY-MM-DD. Natural-language dates and recurrence are not silently converted."
        ) from None


def _parse_priority(value: str, row: int) -> int:
    raw = value.strip()
    if not raw:
        return 2
    try:
        parsed = int(raw)
    except ValueError:
        parsed = 0
    if parsed not in (1, 2, 3, 4):
        raise HTTPException(status_code=422, detail=f"CSV row {row}: priority must be 1–4")
    return parsed


def _valid_text(title: str, notes: str, row: int) -> None:
    if not title.strip() or len(title.strip()) > 240:
        raise HTTPException(status_code=422, detail=f"CSV row {row}: task title must be 1–240 characters")
    if len(notes) > 16000:
        raise HTTPException(status_code=422, detail=f"CSV row {row}: task notes exceed 16000 characters")
    if "\x00" in title or "\x00" in notes:
        raise HTTPException(status_code=422, detail=f"CSV row {row}: NUL control characters are unsupported")


def preview_csv(source: CsvSource) -> dict:
    """Pure deterministic validation; not a database transaction or importer."""
    if len(source.csv_text.encode("utf-8")) > MAX_CSV_CHARACTERS:
        raise HTTPException(status_code=413, detail="CSV file exceeds 500000 UTF-8 bytes")
    try:
        rows = csv.reader(io.StringIO(source.csv_text.lstrip("\ufeff"), newline=""), strict=True)
        header_raw = next(rows, None)
        if header_raw is None:
            raise HTTPException(status_code=422, detail="Empty CSV")
        columns = [h.strip().casefold() for h in header_raw]
        if not columns or len(columns) != len(set(columns)) or any(not h for h in columns):
            raise HTTPException(status_code=422, detail="Duplicate or missing CSV column names")
        expected = {"title"} if source.format == "generic" else {"type", "content"}
        if not expected.issubset(columns):
            raise HTTPException(status_code=422, detail="CSV is missing required columns: " +
                                ", ".join(sorted(expected - set(columns))))
        items: list[dict] = []
        warnings: list[str] = []
        nonempty_unsupported: set[str] = set()
        skipped: dict[str,int] = {}
        indent_parent: dict[int, int] = {}
        allowed_generic = {
            "title","description","due_date","priority","tags","recurrence","parent_row"
        }
        allowed_todoist = {"type","content","description","priority","indent","date"}
        checked = 0
        for number, raw in enumerate(rows, start=2):
            checked += 1
            if checked > MAX_INPUT_ROWS:
                raise HTTPException(status_code=413, detail="CSV contains more than 500 input rows")
            if not raw or all(not x.strip() for x in raw):
                continue
            if len(raw) != len(columns):
                raise HTTPException(status_code=422, detail=f"CSV row {number}: wrong number of columns")
            data = dict(zip(columns, raw))
            allowed = allowed_generic if source.format == "generic" else allowed_todoist
            nonempty_unsupported.update(
                key for key,value in data.items() if key not in allowed and value.strip()
            )
            if source.format == "todoist":
                kind = data["type"].strip().casefold()
                if kind != "task":
                    skipped[kind or "unknown"] = skipped.get(kind or "unknown", 0) + 1
                    if kind == "section":
                        indent_parent.clear()
                    continue
                title = data["content"]
                notes = data.get("description", "")
                due = _parse_date(data.get("date",""), number)
                priority = _parse_priority(data.get("priority", ""), number)
                tags = []
                recurrence = "none"
                indent_text = data.get("indent","1").strip() or "1"
                if indent_text not in {"1","2","3","4"}:
                    raise HTTPException(status_code=422, detail=f"CSV row {number}: INDENT must be 1–4")
                indent = int(indent_text)
                if indent == 1:
                    parent_row = None
                elif indent-1 not in indent_parent:
                    if source.flatten_hierarchy:
                        parent_row = None
                        warnings.append(f"CSV row {number}: orphaned indentation flattened")
                    else:
                        raise HTTPException(status_code=422, detail=f"CSV row {number}: no parent task at indent {indent-1}; enable flatten to import without this relationship")
                else:
                    parent_row = indent_parent[indent-1]
                for n in range(indent, 5):
                    indent_parent.pop(n, None)
                indent_parent[indent] = len(items)
            else:
                title = data["title"]
                notes = data.get("description", "")
                due = _parse_date(data.get("due_date", ""), number)
                priority = _parse_priority(data.get("priority", ""), number)
                tags = [v.strip() for v in data.get("tags", "").split("|") if v.strip()]
                recurrence = data.get("recurrence", "none").strip().lower() or "none"
                if recurrence not in {"none","daily","weekdays","weekly","biweekly","monthly","yearly"}:
                    raise HTTPException(status_code=422, detail=f"CSV row {number}: recurrence unsupported")
                ref = data.get("parent_row", "").strip()
                parent_row = None
                if ref:
                    try:
                        parent_row = int(ref)-1
                    except ValueError:
                        parent_row = -1
                    if parent_row < 0 or parent_row >= len(items):
                        raise HTTPException(status_code=422, detail=f"CSV row {number}: parent_row must reference an earlier imported task")
            _valid_text(title, notes, number)
            if len(items) >= MAX_TASKS:
                raise HTTPException(status_code=413, detail="CSV contains more than 200 importable tasks")
            items.append({
                "title":title.strip(), "description":notes,
                "due_date":due, "priority":priority, "tags":tags,
                "recurrence":recurrence, "parent_index":parent_row
            })
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="Malformed CSV quoting or delimiters") from exc

    if nonempty_unsupported:
        warnings.append("Unmapped non-empty source columns: " +
                        ", ".join(sorted(nonempty_unsupported)))
    for kind, count in sorted(skipped.items()):
        warnings.append(f"Skipped {count} non-task {kind} row(s) from source")
    if not items:
        raise HTTPException(status_code=422, detail="CSV contains no importable task rows")
    return {"format":source.format, "count":len(items), "tasks":items,
            "warnings":warnings, "checksum":checksum(source)}
