# GoreeCloud Tasks HTTP API (v1 development)

All routes below except /healthz require header:

    Authorization: Bearer <32+ character secret>

Send JSON for write operations. API is intended for one trusted operator. Do not bind 0.0.0.0 on an untrusted network. Interactive OpenAPI is provided by FastAPI at /docs on the bound host.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | /healthz | Minimal unauthenticated service liveness, no task content |
| GET | /api/v1/projects | List projects |
| POST | /api/v1/projects | Create {"name":"Family"} |
| GET | /api/v1/tasks?status=active | Active tasks, max 1000 |
| GET | /api/v1/tasks?status=completed | Completed task instances |
| GET | /api/v1/tasks?status=all | All tasks, max 1000 |
| GET | /api/v1/tasks?project_id=...&search=...&due_before=YYYY-MM-DD | Filter results |
| POST | /api/v1/tasks | Create a task |
| GET | /api/v1/tasks/{id} | Retrieve one |
| PATCH | /api/v1/tasks/{id} | Update with required expected_version |
| POST | /api/v1/tasks/{id}/complete | Complete; generate next recurring instance when applicable |
| POST | /api/v1/tasks/{id}/reopen | Reopen a completed instance |
| DELETE | /api/v1/tasks/{id}?expected_version=N | Permanently delete |
| GET | /api/v1/export | Complete portable JSON snapshot |

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

Task data returned also includes UUID id, version, timestamps, completed_at and series_id. Duplicate tag names are normalized case-insensitively. Supported recurrence: none, daily, weekly, monthly; recurrence requires due_date. Priority range 1 (highest) through 4 (lowest).

Update example:

    {"expected_version":1,"title":"Review the updated plan"}

Complete example:

    {"expected_version":2}

A 409 means stale version, already completed, or invalid task state. Reload and reconcile; never blindly retry an edit with a different revision. A 422 means invalid input/missing project; a 401 is a missing or wrong bearer token; a 404 is a nonexistent task. Deletion is irreversible, so maintain a server backup. Authentication and TLS/rate limiting are not included in the web application itself.
