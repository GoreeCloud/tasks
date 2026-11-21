# Daily habits — GoreeCloud Tasks development preview

Daily habits are separate from tasks. They are optional, explicitly created routines with a name, private notes, one check-in per calendar day, a count and a consecutive-day streak. They are not a habit-coaching AI model, reminders, a clinical or mental-health tool, or a production accountability service.

## Data and API

The SQLite schema is **v4**, adding two tables: habits (id, name, description, version, created_at, updated_at) and habit_checkins (habit_id, day, created_at). A unique (habit_id, day) key prevents multiple check-ins on the same day. All mutations use serialized SQLite transactions and expected_version to reject concurrent writes. Editing a habit increments its version. Deleting it removes its check-ins through a verified ON DELETE CASCADE foreign key.

All endpoints are protected by the same single-user bearer token as task routes. For the full route table, see API.md.

- GET /api/v1/habits?as_of=YYYY-MM-DD returns up to 100 habits per page with checked_in_today, total_checkins and current_streak. The client passes its *local* calendar date as as_of; default is server UTC date if absent. The streak is based on consecutive dates ending on the requested day or the immediately preceding day, with a bounded 3650-day computation.
- POST /api/v1/habits creates a new habit; PATCH and DELETE require expected_version.
- POST /api/v1/habits/{id}/checkins adds one date and requires expected_version. Future dates beyond UTC tomorrow are rejected, to allow clients ahead of UTC but not arbitrary future predictions. A duplicate date is an HTTP 409.
- DELETE /api/v1/habits/{id}/checkins/{day}?expected_version=N removes exactly one recorded date and increments revision. Missing dates return 404.
- GET /api/v1/habits/{id}/checkins provides paginated date-only history; 1–1000 per page.
- GET /api/v1/export includes habits and habit_checkins in its protected JSON export. Backups automatically contain both tables.

The React Habits view supports create, edit, delete, check in, undo check-in, read-only streak/status and refresh. No habit state or authentication secret is stored in localStorage. Deleting a habit triggers a user confirmation before a version-checked server deletion.

## Privacy, consistency, and limitations

Habits can reveal personal routines. Apply GoreeShield purpose limitation, privacy and retention policies, Wardveil security controls, and GoreeCloud Identity authorization before any production or family sharing. The current server has only one operator-wide development bearer token: **no per-user ACLs, Identity integration, multiuser sharing, managed backups, production deployment, or device-specific data erasure**. Backup/export copies must be removed separately under their own retention policy.

**Habits are currently online-only**: they are not represented in /sync/bootstrap or /sync/changes, and have no encrypted offline queue, background alarms, weekly/custom schedules, reminders, advanced statistics dashboard or streak recovery. The native Kotlin/Compose Android and Qt Quick Linux clients support listing, creating, editing habit names/notes with expected_version, checking in/undo, and deleting habits. The server validates length and rejects stale edits with HTTP 409, preserving all previous habit check-ins; native calendar-history browsing and offline habit editing are not yet implemented. Do not claim any of these are implemented or imply that an outdated client will receive habit changes through the task change feed. Complete these gates before GoreeCloud Tasks Stable acceptance.

Schema upgrade from previous v1–v3 is additive. Verify an isolated snapshot/restore before any real migration. Tests use disposable databases and synthetic data; no authoritative Vikunja tasks or real personal routines were accessed.
