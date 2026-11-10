# Task duplication — cross-platform parity

**Status:** Development-only increment to draft PR #5. No production release, shared sync, new permissions or personal-data migration.

## Behavior

A user-initiated **Duplicate** copies the task's title, plain-text description, project, due calendar date, and P1–P4 priority into a **new, independent, open task**. It always generates a new task UUID and creation timestamp, resets completed to false and completion timestamps to null, and never modifies the source. This works for open or completed source tasks. A completed source remains completed; its duplicate appears in Open/Inbox or the relevant project view. Trash entries cannot be duplicated directly; restore them explicitly first.

This is intentionally **manual duplication**, not a recurrence scheduler. Dates are copied literally, including past dates. No user-defined repeat rule, reminder, automatic due-date increment, assignee, or subtasks is invented.

## Native and browser implementation

- **Browser:** A per-task **Copy** action creates the task through existing `newTask` validation. The action revalidates the source and target project in a local workspace mutation and retains current schema-1/2 semantics; schema 2 remains required whenever notes must be preserved. A distinct accessible name (**Duplicate [task]**) identifies the action.
- **Linux GTK4:** A native Copy icon button with accessible per-task name invokes a single SQLite `INSERT ... SELECT` transaction on the active table. The operation requires exactly one existing source row; a missing/stale task aborts with no copy. No schema changes or project fallback.
- **Android Compose:** The existing per-task actions menu contains **Duplicate as open task**. A single `SQLiteDatabase` transaction copies the active row, resets completion/history columns, and checks the affected-row count before committing. The copied row receives a fresh UUID and current creation timestamp.

No app sends data to another service. Duplicates are regular tasks and therefore included in subsequent user-initiated versioned portable exports. Local Trash remains excluded as before.

## Tests and release gates

The browser model tests cover immutable completed-source duplication, schema-2 notes, missing projects, distinct identity, and timestamps. Native Linux SQLite tests cover atomic copy and rollback on missing/trash sources, restart persistence, and completed-source reset. GTK smoke exercises the real UI callback and verifies independent open history. Android Robolectric tests cover schema-2 imported completed tasks, retained exact historical timestamps on the source, fresh null metadata on the copy, restart, export and failed-source rollback. Headless Chromium/Firefox synthetic runtime tests exercise the accessible Copy action, two distinct IDs and JSON backup notes preservation.

A final CI run for the exact commit is required before the increment is considered verified. Automated results do **not** replace physical Android/TalkBack, GTK Orca/keyboard/large-text and manual end-to-end release acceptance.

## Next architecture milestone

True **subtasks, labels and recurrence** are separate features requiring a versioned persistence and backup contract, cross-platform migration coverage and sync negotiation. Do not place structured metadata into descriptions or silently omit it from schema-1/2 backups.
