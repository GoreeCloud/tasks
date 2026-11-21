"""RFC 5545 VTODO export for the single-owner task store.

The writer never interpolates raw titles, descriptions or tags into protocol
lines. It escapes TEXT values and folds physical lines at <=75 UTF-8 octets.
No external resources, calendar subscriptions, or reminder side effects.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def text_value(value: str) -> str:
    """Escape the iCalendar TEXT format, rejecting control-character injection."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = "".join(c for c in value if c == "\n" or ord(c) >= 32 and ord(c) != 127)
    return (value.replace("\\", "\\\\")
                 .replace(";", "\\;")
                 .replace(",", "\\,")
                 .replace("\n", "\\n"))


def fold_line(value: str) -> str:
    """Fold physical content lines at a strict 75 *octet* UTF-8 boundary."""
    parts: list[str] = []
    line = ""
    length = 0
    for character in value:
        size = len(character.encode("utf-8"))
        if length + size > 75:
            parts.append(line)
            line = " "  # RFC 5545 continuation (the space consumes one octet).
            length = 1
        line += character
        length += size
    parts.append(line)
    return "\r\n".join(parts)


def utc_stamp(value: str) -> str:
    """Source timestamps may include UTC offsets; serialize all as UTC."""
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError("Task timestamp must be timezone aware")
    return stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_calendar(tasks: list[dict[str, Any]]) -> bytes:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GoreeCloud//Tasks Development//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:GoreeCloud Tasks",
    ]
    for task in tasks:
        due_date = task.get("due_date")
        completed_at = task.get("completed_at")
        tags = task.get("tags") or []
        uid = str(task["id"]).replace("\r", "").replace("\n", "")
        if not uid or any(not (char.isalnum() or char in "._-") for char in uid):
            raise ValueError("Invalid task ID for iCalendar")
        priority = int(task["priority"])
        if priority not in (1, 2, 3, 4):
            raise ValueError("Invalid task priority")
        lines.extend([
            "BEGIN:VTODO",
            "UID:" + uid + "@goreecloud-tasks",
            "DTSTAMP:" + utc_stamp(task["updated_at"]),
            "CLASS:PRIVATE",
            "SUMMARY:" + text_value(str(task["title"])),
            "PRIORITY:" + str({1: 1, 2: 3, 3: 5, 4: 7}[priority]),
            "STATUS:COMPLETED" if completed_at else "STATUS:NEEDS-ACTION",
        ])
        if task.get("description"):
            lines.append("DESCRIPTION:" + text_value(str(task["description"])))
        if due_date:
            # DATE, not a UTC instant; preserve the user's intended calendar day.
            parsed = datetime.strptime(due_date, "%Y-%m-%d")
            lines.append("DUE;VALUE=DATE:" + parsed.strftime("%Y%m%d"))
        if completed_at:
            lines.append("COMPLETED:" + utc_stamp(completed_at))
        if tags:
            lines.append("CATEGORIES:" + ",".join(text_value(str(tag)) for tag in tags))
        lines.append("END:VTODO")
    lines.append("END:VCALENDAR")
    return ("\r\n".join(fold_line(line) for line in lines) + "\r\n").encode("utf-8")
