# Todoist → GoreeCloud Tasks migration gate

**Status: Not executed.** Todoist Free remains interim authority only for obligations already reconciled into Todoist. Unmigrated legacy obligations remain with their original authoritative source.

## Safe migration sequence

1. Verify current task-authority registry and provider limits; do not assume all legacy obligations already migrated.
2. Snapshot/export Todoist and preserve metadata, original IDs and URLs; verify readable archives.
3. Map projects, sections, task titles, descriptions, checklists/subtasks, labels, priorities, due dates/timezones, recurrence, attachments and comments without silent loss. Record limitations and original source IDs.
4. Implement an idempotent, dry-run-first importer, conflict resolution, privacy checks, and duplicate detection.
5. Import into an isolated non-production profile, read back every resulting record and reconcile source counts plus explicit exclusions against destination counts.
6. Validate live task editing, notifications, sharing/security, recurrence, mobile/desktop/online/offline, backup/restore and rollback with representative data.
7. Freeze or reconcile concurrent Todoist edits; complete a final delta import; update canonical GoreeCloud governance in place **only after** Stable and owner acceptance.
8. Retain recoverable Todoist data until separately authorized retirement. Never assume that shipping a codebase or CI success grants task authority.

No automated live synchronization or importer is claimed at this stage.
