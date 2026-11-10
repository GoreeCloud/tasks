"""Offline-only deterministic iCalendar VTODO preview for GoreeCloud DAV.

Does not fetch tasks, write files, open sockets, manage credentials, grant
user consent or perform cross-product sync. The caller owns those boundaries.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import re
from outbox import OutboxError, canonical_uuid

_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_UNSAFE_FORMAT = frozenset((0x061C, 0x200E, 0x200F, 0x2028, 0x2029))
MAX_PREVIEW_BYTES = 8192


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise OutboxError("Invalid UTC task timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OutboxError("Invalid UTC task timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OutboxError("Task timestamp must be UTC")
    return parsed.strftime("%Y%m%dT%H%M%SZ")


def _summary(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 240:
        raise OutboxError("Invalid Task summary")
    for ch in value:
        point = ord(ch)
        if (point in _UNSAFE_FORMAT or 0x202A <= point <= 0x202E
                or 0x2066 <= point <= 0x2069 or 0xD800 <= point <= 0xDFFF
                or (point < 32 and ch not in "\r\n") or point == 127):
            raise OutboxError("Task summary contains an unsafe control")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return (value.replace("\\", "\\\\").replace("\n", "\\n")
            .replace(";", "\\;").replace(",", "\\,"))


def _fold(line: str) -> list[str]:
    if not line or "\r" in line or "\n" in line:
        raise OutboxError("Invalid iCalendar logical line")
    result = []
    segment = ""
    used = 0
    for ch in line:
        octets = len(ch.encode("utf-8"))
        if used + octets > 75:
            result.append(segment)
            segment = " "
            used = 1
        segment += ch
        used += octets
    result.append(segment)
    return result


def vtodo_preview(task: dict) -> bytes:
    """Serialize only an explicitly selected live Tasks API snapshot.

    This is a read-only preview. Never infer user sharing permission from a
    successful serialization. Priority, recurrence, alarm, assignment and
    foreign DAV properties are intentionally not represented.
    """
    if not isinstance(task, dict):
        raise OutboxError("Expected a task snapshot")
    uid = canonical_uuid(task.get("id"))
    if task.get("deleted") is not False or type(task.get("completed")) is not bool:
        raise OutboxError("Only live tasks with explicit completion may be exported")
    revision = task.get("revision")
    if type(revision) is not int or not 1 <= revision <= 2147483647:
        raise OutboxError("Invalid task revision for VTODO")
    summary = _summary(task.get("title"))
    stamp = _timestamp(task.get("updatedAt"))
    due = task.get("due")
    if due is not None:
        if not isinstance(due, str) or _DATE.fullmatch(due) is None:
            raise OutboxError("Invalid Task due date")
        try:
            if date.fromisoformat(due).isoformat() != due:
                raise ValueError("Noncanonical due date")
        except ValueError as exc:
            raise OutboxError("Invalid Task due date") from exc

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//GoreeCloud Tasks//VTODO Preview//EN",
        "BEGIN:VTODO",
        "UID:urn:uuid:" + uid,
        "DTSTAMP:" + stamp,
        "SEQUENCE:" + str(revision - 1),
        "CLASS:PRIVATE",
        "STATUS:" + ("COMPLETED" if task["completed"] else "NEEDS-ACTION"),
        "SUMMARY:" + summary,
    ]
    if due is not None:
        lines.append("DUE;VALUE=DATE:" + due.replace("-", ""))
    lines.extend(("END:VTODO", "END:VCALENDAR"))
    encoded = ("\r\n".join(segment for line in lines for segment in _fold(line))
               + "\r\n").encode("utf-8")
    if len(encoded) > MAX_PREVIEW_BYTES:
        raise OutboxError("VTODO preview exceeds size limit")
    return encoded
