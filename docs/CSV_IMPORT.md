# Preview-first CSV task import — development preview

GoreeCloud Tasks can import an explicitly selected, local CSV file into the single-user self-hosted Tasks server. **No Todoist or TickTick account is connected. No live task data is copied or migrated automatically.** The user controls the file, destination project, preview and final confirmation.

## Supported formats

### Generic task CSV

UTF-8 CSV with a header. Required column: title. Optional fields:

| Column | Format and meaning |
| --- | --- |
| title | 1–240 characters, required |
| description | Optional task notes, up to 16,000 characters |
| due_date | ISO YYYY-MM-DD or blank; no due time or timezone conversion |
| priority | 1–4, 1 being highest; default 2 |
| tags | Separate tags with the pipe character; at most 12, max 36 characters each |
| recurrence | none (default), daily, weekdays, weekly, biweekly (14 days), monthly, yearly; a recurring task needs a due date |
| parent_row | Optional 1-based index of a previously imported task in this file; no cycles |

Example (synthetic data, not a real account export):

    title,description,due_date,priority,tags,recurrence,parent_row
    Plan a picnic,Find a suitable park,2026-12-01,2,personal|weekend,none,
    Make a list,,2026-11-28,3,personal,none,1

### Todoist *project CSV subset*

Use the official project export CSV containing TYPE, CONTENT, PRIORITY, INDENT, DESCRIPTION, DATE and other headers. Supported task rows map task content to title, notes, numeric priority and indentation levels 1–4 to parent links. DATE must be an unambiguous ISO YYYY-MM-DD or blank. Non-task sections, notes and comments are skipped with explicit warnings; unsupported nonempty fields appear in warnings, including assignees, timezones or date language. Orphaned indentation is rejected unless the user explicitly selects the flatten hierarchy option, which is reported in preview warnings.

**Unsupported:** Natural-language recurring expressions or dates, due times, timezones, deadlines, full RRULE, arbitrary custom provider columns, attachments, assigned users, comments, completed-state migration, reminders, personal filters and embedded checklists. These are not silently converted to different values; invalid dates reject the file. The user should review and reconcile excluded content manually before declaring any migration complete.

Todoist's official CSV format reference: https://www.todoist.com/help/account-and-billing/security/import-or-export-a-project-as-a-csv-file-in-todoist-YC8YvN

TickTick bulk backup CSV follows a separate provider layout and is **not** supported by this importer. Do not label TickTick migration complete.

## Two-step API

Both endpoints use the existing single-user Authorization: Bearer token; they are not public.

1. POST /api/v1/import/csv/preview with JSON format, csv_text, optional project_id and flatten_hierarchy. It validates the entire file and returns a preview of task candidates, warnings and SHA-256 checksum. **No database task mutation occurs.** The preview may contain private titles and descriptions; handle its response as sensitive.
2. POST /api/v1/import/csv with the exact same fields, the returned checksum, and a required unique Idempotency-Key (8–128 safe ASCII characters). It revalidates every entry and checksum before acquiring the SQLite BEGIN IMMEDIATE lock; then atomically creates all tasks with generated UUIDs, parent links and changefeed upserts. A failure rolls the entire import back. A replay with the same idempotency key and unchanged content returns the original result without duplicate insertion. Reusing that key for different input returns HTTP 409.

The browser retains the same preview and idempotency key if the server response is lost. It never uploads files merely because they were selected and never stores imported text in localStorage or IndexedDB. A direct API consumer can compute a matching checksum without making an earlier preview call, so API authorization and idempotency are still required; the **web workflow** is what enforces a human preview and confirmation.

## Safety and bounds

Input is limited to 500,000 UTF-8 bytes, 500 CSV input rows and 200 task records per batch. Header duplicates, ragged rows, malformed quoting, bad numeric fields, unsupported recurrence, invalid title or notes, excessive tags, ambiguous dates, orphan hierarchy (unless explicitly flattened), and missing destination projects return validation errors rather than applying a partial import. Preview-only errors must not expose the text of private notes in stack traces or logs.

This is a development-stage tool, not an automatic migration, backup restore or source-of-truth handoff. The app remains a single-user bearer-token server; it has no per-account provider API access, Identity ACLs, production TLS gateway/rate limits, fully verified backup restore, device acceptance or Stable release. Before importing real data, a user must authorize the destination and have a verified disposable backup. Do not modify the currently authoritative Vikunja task system without a separate approved handoff.
