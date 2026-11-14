"""Read-only, fail-closed Tasks → Calendar VTODO compatibility preflight.

The output contains only fixed reason codes, never task identities or content.
This does not change a VTODO, grant sharing consent, or perform an import.
The Calendar target is the source-reviewed, unmerged November 2026 draft.
"""
from __future__ import annotations

from outbox import OutboxError
from vtodo_export import vtodo_preview

PROFILE = "tasks.vtodo-preview.v1"
TARGET = "calendar.vtodo-draft.20261111"

def calendar_import_preflight(task: dict) -> dict:
    """Describe semantic blockers before attempting any cross-product import.

    This API deliberately cannot authorize a transfer or supply a converted
    payload. A future source-backed adapter must preserve privacy, revision,
    due-date and unknown-field semantics, or ask for explicit user decisions.
    """
    if type(task) is not dict:
        raise OutboxError("Expected a task snapshot")
    payload = vtodo_preview(task)
    lines = payload.decode("utf-8").replace("\r\n ", "").split("\r\n")
    reasons = []

    # Inspect the emitted *wire profile*, not assumed source data. The target
    # parser rejects these properties, and dropping either loses semantics.
    if any(line.startswith("SEQUENCE:") for line in lines):
        reasons.append("revision_not_supported")
    if any(line.startswith("CLASS:") for line in lines):
        reasons.append("privacy_class_not_supported")
    if any(line.startswith("DUE;VALUE=DATE:") for line in lines):
        reasons.append("date_only_due_not_supported")

    # Calendar limits imported summaries to 160 characters; source allows 240.
    title = task["title"]
    if len(title.strip()) > 160:
        reasons.append("title_too_long_for_calendar")

    # Tasks's preview does not export priority. Calendar interprets an absent
    # PRIORITY as P3, which would silently alter other source priorities.
    priority = task.get("priority")
    if type(priority) is not int or priority not in (1, 2, 3, 4):
        reasons.append("priority_not_proven")
    elif priority != 3:
        reasons.append("priority_not_exported")

    # The target validates DTSTAMP but does not retain Tasks's updatedAt,
    # so even with supported properties, full revision history is not portable.
    reasons.append("update_timestamp_not_preserved")

    # Do not enumerate unknown/private fields in diagnostics, because callers
    # could mistakenly interpret absent reasons as proof of complete fidelity.
    return {
        "source_profile": PROFILE,
        "target_profile": TARGET,
        "status": "blocked" if reasons else "compatible",
        "reason_codes": reasons,
        "mutates_data": False,
        "requires_user_consent": True,
        "full_fidelity_verified": False,
    }
