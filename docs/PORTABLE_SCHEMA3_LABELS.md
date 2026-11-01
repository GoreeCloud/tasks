# Portable schema 3 — first-class task labels

**Status:** Cross-platform development increment on draft PR #5. **Not** a Stable release, a task-authority cutover, or a production/device migration.

## Versioned portable format

- **Schema 1:** Existing title, priority, date, project and completion metadata. No description or labels.
- **Schema 2:** Schema 1 plus a required `description` string on every task. No labels.
- **Schema 3:** Schema 2 plus a required `labels` array on every task, including `[]` for unlabelled tasks. No other field or timestamp contract changes.

Each task can have up to **8 ordered, distinct, plain-text labels**, each **1–32 UTF-16 code units**. Labels preserve case, internal whitespace and Unicode but must already be trimmed, contain no commas, control characters or unmatched surrogates, and cannot repeat exactly. Duplicate or invalid labels cause validation failure before any write. The comma-separated native/browser entry is only a UI parser: the persisted representation is an explicit array.

Export chooses schema 1 if there are no notes or labels; schema 2 if notes exist but no labels; schema 3 if any task has labels. The browser may retain a previously upgraded schema version to avoid losing explicit empty arrays. **Never downgrade** a schema-3 task by silently removing `labels`: schema-1/2 validation rejects the field. A schema-3 backup requires a schema-3-aware receiving app; existing releases that support only 1/2 cannot restore it.

Portable JSON exports include active and completed tasks and projects. **Local Trash remains excluded.** Backups still exclude credentials, app settings, remote sync information, OS state and history beyond active task completion metadata. Imports remain user-initiated and guarded to an entirely empty local workspace.

## First-party implementation

- **Browser:** Local editor, capture and task-row label chips use semantic GC UI styling and plain text, not HTML. Versioned snapshot serialization and validation preserve labels through refresh, Trash, restoration, and duplicate. Local storage is still localStorage, with the existing stale-tab guard and its documented concurrency limits.
- **Linux GTK4:** An additive `labels_json TEXT NOT NULL DEFAULT '[]'` SQLite column is applied to active and deleted tables, including legacy on-disk databases, without rewriting other rows. Creating, editing, duplicating, bulk Trash, recoverable Trash and importing/exporting all retain labels. Native UI accepts a comma-separated list and shows labels in row metadata.
- **Android Compose:** SQLite database **v7** adds the same default-empty JSON array column to active and deleted tables. The migration checks column existence to handle legacy versions safely. Compose exposes native capture/edit controls and preview; SQLite writes and Trash moves remain transactional. Portable schema-3 parsing verifies every label before the guarded import transaction.

No account permissions, Internet permissions, third-party SDKs, migrations of personal records, deployment or cross-device sync were added. This is **label metadata**, not first-class saved filter definitions, label-based alerts, label-color settings, recurring task rules or subtasks.

## Tests and acceptance gates

`fixtures/portable/schema3-synthetic.json` contains Unicode labels, an empty label list, notes, project references and precise historical completion timestamps. Browser Node, Linux Python/SQLite and Android JVM/Robolectric use this one contract fixture. Tests cover strict format parsing, invalid labels, legacy downgrade rejection, additive migration, atomic Trash and restore, duplication and portable export/import. Browser Chromium/Firefox synthetic end-to-end acceptance also edits, exports and reloads schema-3 data in an independent empty browser context.

**Still required:** Full CI on the exact final commit, physical Android device migration/large-text/TalkBack, Linux Orca/keyboard and distro testing, human GC UI visual acceptance, recovery and release sign-off, a versioned sync contract, and a safe cutover plan from Todoist. PR #5 remains draft and unmerged until the appropriate acceptance gates are satisfied.
