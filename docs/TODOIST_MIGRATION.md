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

## Current implementation and verified boundaries

The inherited Vikunja Todoist OAuth importer **exists in source**. GoreeCloud Tasks has now added:

- Source-graph preflight validation before creating imported projects or tasks. Missing projects, sections, labels, task parents, notes and reminders, duplicate identifiers, and cyclic task ancestry produce an error rather than a superficially successful partial conversion.
- A fix retaining subtask identities while their notes and reminders are converted; nested child relationships are covered by Go regressions.
- Nested Todoist project ancestry is mapped into parent/child destination project references, including child-first source order; missing/cyclic ancestry is rejected. Final persisted database hierarchy still needs readback verification.
- Task-note attachments now fail closed when the source URL is opaque, missing, credential-bearing, or fails download. Downloads use the configured maximum file size and an SSRF-safe HTTP client. Unsupported project-note attachments remain a blocking error.
- The Todoist import screen displays a fidelity warning and requires post-import reconciliation rather than suggesting universal success.
- Todoist's OAuth callback no longer automatically starts writing imported records. It now displays an explicit user-acknowledgement checkbox after authorization; the import action is disabled until consent is given. Re-import begins with a fresh authorization and consent step. This is **not** a substitute for a genuine dry-run preview or deduplication.
- The importer now rejects monthly and yearly Todoist recurrence instead of converting them to 30- and 365-day repeats that change real calendar schedules. Accurate calendar-month/year and DST/timezone semantics remain unresolved and must be tested before Stable.
- Preflight now rejects duplicate or missing source note, project-note, and reminder identities as well as source task/project mismatches on note associations.
- GitHub Actions `Todoist Import Integrity` for the package tests. Initial successful test evidence: https://github.com/GoreeCloud/tasks/actions/runs/38082667040.

- The preflight rejects whitespace-only project/section/task titles and Todoist tasks flagged as having more notes than the downloaded snapshot; skipping such records would make a complete-looking migration misleading.
- A pre-insertion reconciliation now checks source vs converted **project, section, task, subtask, reminder and downloadable attachment counts**. Mismatches abort conversion before destination DB writes. It deliberately contains no titles, note text or signed file URLs.
- Empty OAuth token responses and completed-task detail HTTP 404s now fail explicitly rather than allowing an empty or incomplete successful import. OAuth error bodies are no longer copied into diagnostic errors.
- A shared Todoist HTTP decoder checks that OAuth, sync snapshots, completed-task pages/details and archived-project pages/details return HTTP 2xx **before** JSON decoding. It closes response bodies on errors and avoids including upstream error bodies, signed URLs or credentials in diagnostics. Focused Go tests cover 2xx, redirects, 401, 429, 500, malformed JSON, missing responses and body closure.
- Completed-task and archived-project pagination now tracks source cursors independently and rejects a repeated cursor rather than looping or silently treating duplicated source pages as progress. This does not prove a complete or stable upstream snapshot.
- Completed-task API pages are checked for missing IDs, project references, completion timestamps and invalid project metadata before sorting or dereferencing; returned task details must match the requested task and project identities. Archived-project pages reject malformed or duplicate project identities. This prevents partial or wrong-record imports but does not replace exact source-to-destination validation.
- A completed task from a **deleted Todoist project** now causes an explicit import error, rather than silently excluding the task from the reconstructed source.
- The OAuth authorization URL no longer uses a predictable fixed `state` value when the cryptographic generator fails. Authorization fails closed instead, and URL query parameters are encoded. **OAuth callback state binding/validation remains unimplemented**; this change alone does not establish CSRF protection.


**Still missing:** localized Todoist import confirmation copy across supported languages, user-facing read-only dry-run previews, persistent source-ID-to-destination-ID mapping, repeated-import deduplication, persisted hierarchy/readback parity, advanced recurrence and timezone fidelity, exact note/comment content and authorship, attachment ownership/association fidelity, full destination readback, exact corpus reconciliation, backup/restore, conflict recovery, and rollback. **Pre-insertion count matching is not equivalent to post-insertion data reconciliation or a verified live migration.** The importer may be exercised only in controlled test environments until these gates pass.

No import has been run against the owner's live Todoist data and no automatic synchronization, complete fidelity, authority cutover, or Stable acceptance is claimed.
