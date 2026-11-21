# GoreeCloud Tasks HTTP API (v1 development)

All routes below except /healthz require header:

    Authorization: Bearer <32+ character secret>

Send JSON for write operations. API is intended for one trusted operator. Do not bind 0.0.0.0 on an untrusted network. Interactive OpenAPI is provided by FastAPI at /docs on the bound host.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | /healthz | Minimal unauthenticated service liveness, no task content |
| GET | /api/v1/projects | List projects |
| POST | /api/v1/projects | Create {"name":"Family"} |
| GET | /api/v1/tasks?status=active | Active tasks, default 1000 per page |
| GET | /api/v1/tasks?status=completed | Completed task instances |
| GET | /api/v1/tasks?status=all | All tasks, max 1000 |
| GET | /api/v1/tasks?project_id=...&search=...&due_before=YYYY-MM-DD&limit=100&offset=0 | Filtered, deterministic page |
| POST | /api/v1/tasks | Create a task |
| GET | /api/v1/tasks/{id} | Retrieve one |
| PATCH | /api/v1/tasks/{id} | Update with required expected_version; optional Idempotency-Key supports safe retry after a lost response |
| POST | /api/v1/tasks/{id}/complete | Complete; generate next recurring instance when applicable |
| POST | /api/v1/tasks/{id}/reopen | Reopen a completed instance |
| DELETE | /api/v1/tasks/{id}?expected_version=N | Permanently delete |
| POST | /api/v1/import/csv/preview | Authenticated, non-writing generic/Todoist-subset CSV validation and checksum |
| POST | /api/v1/import/csv | Atomic, explicitly confirmed import: checksum and required Idempotency-Key, max 200 tasks |
| GET | /api/v1/export | Complete portable JSON snapshot |
| GET | /api/v1/export.ics | Authenticated VTODO iCalendar download (max 5000 tasks) |
| GET | /api/v1/habits?as_of=YYYY-MM-DD&limit=100&offset=0 | List daily habits, check-in status, total count and bounded streak as of local date |
| POST | /api/v1/habits | Create a daily habit with name and optional description |
| PATCH | /api/v1/habits/{id} | Edit with expected_version |
| DELETE | /api/v1/habits/{id}?expected_version=N | Erase habit and its check-in history |
| GET | /api/v1/habits/{id}/checkins | List recorded dates, bounded pagination |
| POST | /api/v1/habits/{id}/checkins | Add check-in with JSON day and expected_version |
| DELETE | /api/v1/habits/{id}/checkins/{day}?expected_version=N | Undo one check-in |
| GET | /api/v1/sync/bootstrap | Consistent task/project snapshot with cursor; up to 5000 entities each |
| GET | /api/v1/sync/changes?after=0&limit=100 | Incremental cursor feed with updates and deletion tombstones |

Create example:

    {
      "title": "Review the plan",
      "description": "Discuss updates",
      "project_id": null,
      "due_date": "2026-11-25",
      "priority": 2,
      "tags": ["planning"],
      "recurrence": "weekly"
    }

Task data returned also includes UUID id, version, timestamps, completed_at, series_id and optional parent_id. Creating/updating a child uses parent_id, which must reference an active task; cycles and self-parenting return HTTP 422. Parent completion with unfinished descendants returns HTTP 409. Deleting a parent detaches children, increments their versions and emits sync changes. Duplicate tag names are normalized case-insensitively. Supported recurrence: none, daily, weekly, monthly; recurrence requires due_date. Priority range 1 (highest) through 4 (lowest).

Update example:

    {"expected_version":1,"title":"Review the updated plan"}

Complete example:

    {"expected_version":2}

Optional Idempotency-Key on project/task creation and completion allows safe identical retries; a changed payload for a reused key produces 409 and a deleted task's scrubbed receipt produces 410. A 409 also means stale version, already completed, or invalid task state. Reload and reconcile; never blindly retry an edit with a different revision. A 422 means invalid input/missing project; a 401 is a missing or wrong bearer token; a 404 is a nonexistent task. Deletion scrubs previous task feed payloads and matching retry receipts while retaining tombstones; it is irreversible, so maintain an independently verified backup under an approved retention policy. Authentication and TLS/rate limiting are not included in the web application itself.
