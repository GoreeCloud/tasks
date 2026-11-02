# Browser-local Trash and recovery

**Status:** development-only; browser data is not synchronized.

## Persistence and upgrade

- Existing browser-local schema-1 data at `goreecloud.tasks.local.v1` remains readable. Reading does **not** mutate or discard existing storage. On the first *successful* save, the same key is replaced with an internal versioned envelope (`goreecloud.tasks.local.v2` format).
- The envelope holds a validated schema-1 or schema-2 **active workspace** and a separate validated **Trash** collection in **one** localStorage value. Saving writes that value in one `setItem` call, so a completed delete does not persist only half of its active/Trash change.
- Deleted task records retain their original IDs, completion/creation timestamps (including microseconds), project associations, priorities, due dates, and full text. Trash remains available across page reloads in the same browser profile.
- The Trash view supports individual Restore actions. A shortcut restores the most recently deleted task. Task-ID conflicts and missing original projects fail closed, leaving recovery records intact.
- Trash keeps at most **1,000 records**. Combined storage is capped at **3 MiB** of serialized UTF-8 data. At either limit, new writes **fail** rather than deleting older history.
- An explicit portable JSON import replaces *active* tasks/projects but preserves local Trash. IDs that collide with Trash reject the complete import. If the imported workspace omits a previously linked project, the deleted record retains its original link and cannot be restored until that project ID exists again.

## Portable backup distinction

**Export data** produces cross-platform **schema-1 JSON** for tasks without descriptions, or **schema-2 JSON** when notes must be preserved, with active tasks and projects. Older schema-1-only clients cannot restore schema-2 notes; upgrade the receiver first. It intentionally **excludes Trash**. An independent, verified backup is necessary to survive browser-profile removal, device loss, storage eviction, or other failure. Do not confuse durable browser-local recovery with cloud storage or disaster recovery.

## Concurrency and security limitations

- The app still uses `localStorage` as its authoritative browser store, with a stale-tab check and cross-tab `storage` notifications. **Simultaneous** edits from two tabs can still race between checking and writing; only moving to a transactional architecture such as IndexedDB can close that gap.
- An unreadable, oversized, or malformed local snapshot is **not repaired or replaced automatically**. Editing and export are disabled. A user explicitly choosing backup import can replace unreadable data.
- Existing tasks and Trash are private to this browser profile; no Internet permission, remote account, credentials, background sync, or other user files are involved.
- This feature was validated through pure Node regression tests (legacy migration, reload, precision preservation, invalid storage, duplicate IDs, missing projects, capacity), but browser visual, keyboard and screen-reader acceptance still require separate QA.
