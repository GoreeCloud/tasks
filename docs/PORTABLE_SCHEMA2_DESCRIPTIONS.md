# Portable schema 2 — task descriptions

**Status:** New development-only cross-platform capability in draft PR #5. No production release, personal-data migration or Todoist cutover.

## Wire format

Existing schema 1 remains accepted without modification. Schema 2 has the same projects and tasks fields and timestamps as schema 1, with one additional **required** plain-text `description` string on every task. An empty description is valid. Descriptions are bounded to **2,000 UTF-16 code units**, including multiline Unicode and emoji; unpaired surrogates are rejected. Existing task identity, priority, due date, completion and exact timestamp strings are unchanged.

Export behavior is fail-safe: a task collection with no notes may be exported as schema 1 for legacy portability; an active task with notes forces schema 2 with a description field for **all** exported tasks. The browser may retain schema 2 once it has been upgraded locally, even when notes have subsequently been cleared. **An explicitly provided description in schema-1 JSON is rejected** instead of being stripped. Unknown unrelated fields continue to be discarded by the strict backup validator, and nonportable app preferences are never included.

The two versioned formats are **not** universally backward-readable: an older schema-1-only build cannot import a schema-2 file. Upgrade the receiver to schema-2 support first. Never downgrade an active workspace without preserving and verifying a schema-2 backup.

## Client implementation

- **Browser:** Plain-text Notes capture, editor and list preview; existing same-key local active/Trash envelope persists the description and refuses invalid writes before commit. Editing titles, priority or completion does not erase notes. The browser remains localStorage-based and does not yet guarantee transactionality across simultaneous tabs.
- **Linux:** Additive nullable-free `description TEXT NOT NULL DEFAULT ''` columns on active and deleted SQLite tables; idempotent startup migration without rewriting existing rows. CRUD, atomic Trash and bulk Trash copy all preserve descriptions. Native GTK editor and capture expose plain-text notes. Schema-1 backup imports default to empty notes.
- **Android:** Additive on-device SQLite database version **6**, carrying descriptions through active rows, Trash, restoration and edits. Jetpack Compose exposes optional notes during capture/edit and a concise list preview. JSON export emits schema 2 only when notes require it; import into a **completely empty** local database remains guarded and transactional. No new permissions, dependency, network access or automatic cloud backup.

## Description search across clients

All three first-party clients now apply the existing local search field to **task titles and descriptions**, with a trimmed, case-insensitive literal-substring query. A hit in either field is enough; existing project, Today, Upcoming, priority and Completed view boundaries remain enforced. Recoverable device-local Trash searches both fields without exporting Trash, changing its order, or modifying task records.

- **Browser:** `selectTasks` and the local Trash view use plain-text matching; escaped HTML and notes remain text, never injected into markup.
- **Linux:** Parameterized SQLite `LIKE` queries match titles or descriptions and explicitly escape `%`, `_` and backslashes so user-entered characters remain literal rather than SQL wildcards. The GTK search field is labeled for both titles and notes.
- **Android:** Pure `TaskViews` filtering provides the same behavior for active/completed views and separate recoverable Trash filtering; Compose uses the same view logic.

Matching is local-only; no data is uploaded or indexed by a third party. SQLite's built-in Unicode case folding differs from JavaScript/Kotlin for some non-ASCII scripts, so full multilingual collation parity remains an acceptance item. No schema, backup version, database permission or network behavior changes were needed for search.

**Local Trash remains excluded** from portable JSON, including schema 2. App data, settings, deleted history, account credentials and files are not copied into backups. An end-to-end *full-device* recovery requires a verified SQLite snapshot as well as user-initiated portable export.

## Tests and acceptance gates

Synthetic `fixtures/portable/schema2-synthetic.json` is shared by browser Node, Linux Python/SQLite and Android JVM/Robolectric tests. Cases cover multiline Unicode, empty description, exact completed timestamp precision, schema-1 import, schema-2 import/export, editor persistence, SQLite migration, atomic Trash, rollback and overlong/invalid text.

The headless Chromium and Firefox suite also captures, edits, exports and restores a schema-2 description into a different empty browser profile without touching personal task records. These are development test results, not Stable acceptance.

**Still required:** final four-job GitHub Actions result at the exact head, Android on-device migration/Compose screen reader and font-size testing, Linux Orca/keyboard/full distro tests, recovery with actual user-approved device/provider combinations, lifecycle/rollback, and compatibility verification against any future sync API. Do not merge or deploy this schema evolution before those gates.

## Manual task duplication and descriptions

A task can be manually duplicated on each native client and browser without changing this portable format: the new, incomplete task retains its plain-text description, priority, project and due date but has a fresh ID/creation time and no completion history. Schema 2 continues to be mandatory when active notes would otherwise be lost. See [manual duplication contract](TASK_DUPLICATION.md).
