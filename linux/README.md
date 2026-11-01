# GoreeCloud Tasks — Native Linux Development Install

**Stage:** development-quality installer, not a packaged or Stable Linux release.

This project is a first-party Python/PyGObject GTK4 and libadwaita desktop app. It launches without any embedded website or Electron/WebView shell. Its SQLite database is device-local.

## Requirements

Install Python 3, GTK4, libadwaita 1.x, PyGObject and the appropriate GObject Introspection packages from your operating-system package manager. On Ubuntu 24.04, typical dependencies are `python3`, `python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`.

## Development installation

Inspect the shell scripts before use. From the repository root:

```sh
sh linux/install.sh
# Launch from the desktop menu or via:
~/.local/bin/goreecloud-tasks

# Remove app files but preserve the SQLite database:
sh linux/uninstall.sh

# Verify an isolated user-local install/uninstall without touching personal data:
sh linux/tests/test_install.sh
```

The installer includes the native `theme.py` appearance module alongside the GTK application. The isolated installation test checks its presence and checks removal when uninstalling; appearance preferences live separately in the private XDG config location and remain preserved when application files are uninstalled.

The installer copies the native application into `$XDG_DATA_HOME/goreecloud-tasks/application` (or `~/.local/share/goreecloud-tasks/application`), creates a launcher under `~/.local/bin` and a desktop entry and icon in XDG user-local locations. It does not require sudo or install dependencies.

The application creates task database files with private permissions (0600) and rejects symlinked database paths. The default XDG task directory is restricted to the owner (0700).

The database at `$XDG_DATA_HOME/goreecloud-tasks/tasks.sqlite3` is intentionally **preserved on uninstall**. To delete task data, an explicit separate user action is required. Uninstall is not proof of data backup. There are no automatic updates or signing guarantees yet.

## Portable task backups (experimental)

The Linux CLI can export projects and tasks using the **same validated schema-1 JSON format as the browser**. It includes task IDs, priorities, due dates, completion timestamps and project references. A backup file is created with private file permissions and will **not** overwrite an existing file.

```sh
# Use the default device-local SQLite store; create a new JSON file:
python3 linux/backup.py export --file ~/Documents/goreecloud-tasks-backup.json

# On a separate test database, restore without overwriting existing tasks:
python3 linux/backup.py --database /tmp/goreecloud-tasks-import-test.sqlite3 import --file ~/Documents/goreecloud-tasks-backup.json
```

**Recoverable local Trash:** The Linux app has a **Trash** view with a native
**Restore** button. Deletion moves a task into a separate SQLite table atomically
instead of destroying its metadata; restoration preserves its original ID,
project link, due date, priority, completion status and timestamps. Deleted
tasks survive application restarts and are preserved with the local SQLite
database during uninstall. Existing databases gain the Trash table through a
non-destructive additive migration. If a task ID already exists in the active
store, or its original project no longer exists, restoration fails without
altering either row; it never silently overwrites or reassigns records.

**Portable JSON exports deliberately exclude Trash history** to preserve
cross-platform schema-1 compatibility. They contain current tasks and projects,
not deleted records. Retaining the original SQLite database (including its WAL
files or a verified SQLite snapshot) is necessary to preserve deleted tasks
across device moves. There is currently no permanent-delete/empty-trash command;
this is a conservative recovery-first foundation, not a complete lifecycle
policy. Test the restore operation with synthetic data before relying on it.

The GTK task list also exposes **Overdue** and **Next 7 days** calendar views, an All/P1–P4 priority filter, Smart/Due date/Title sorting, and multi-selection with atomic batch complete/reopen/priority/project moves and recoverable Trash transfers. See [native bulk-edit safety](../docs/NATIVE_BULK_OPERATIONS.md). These operate on read-only SQLite queries rather than modifying tasks. The seven-day range means today through day six and works across daylight-saving and year boundaries. See [native parity notes](../docs/NATIVE_VIEW_PARITY.md).

The native GTK interface also exposes **Export JSON** and **Import JSON** file dialogs using the same guarded implementation. It also provides a native **Edit** dialog for task title, priority, due date and project; changes are validated and applied together without clearing completion history. Completion toggles are idempotent: repeating an already-completed state does not rewrite the original completion timestamp stored in portable backups.

**Import requires an empty task database, including an empty local Trash,** and validates the entire JSON snapshot before committing any records. Even if no active tasks remain, import refuses to mix a new backup with existing deleted-task history; use a new database for recovery instead. It never replaces live or trashed records. Export refuses a missing SQLite database or existing output file, so it cannot silently provide an empty misleading backup. Test backup compatibility and verify real recovery before using it for important work. Android import/export is now implemented and a limited Android 16 native document-picker smoke test passed; comprehensive provider, completed-task, and release acceptance is still pending. File-dialog interactions require full platform-specific GUI acceptance beyond the initial smoke launch.

## GTK runtime smoke (optional)

On a Linux machine with GTK4, libadwaita, PyGObject and `xvfb-run` installed:

```sh
xvfb-run -a python3 linux/tests/gui_smoke.py
xvfb-run -a /usr/bin/python3 linux/tests/gui_window_smoke.py 600
xvfb-run -a /usr/bin/python3 linux/tests/gui_window_smoke.py 940
```

This exercises the actual native window, task edit dialog, Trash/Restore actions and SQLite persistence
using a **temporary XDG_DATA_HOME**. The same headless GTK4 test is run in
GitHub Actions on Ubuntu 24.04 so source commits cannot silently break GTK
startup or the tested edit flow. It never reads or writes the user's normal
Tasks database. The smoke test does not replace visual, keyboard-navigation,
accessibility or multi-distribution acceptance. The GC UI stylesheet uses
libadwaita's adaptive palette variables for light/dark themes; GTK CSS does
not support browser `@media` rules.

**Appearance:** The native header offers Light/Dark and GC UI semantic accent choices (Neutral, Lagoon, Moss, Ember, Ocean and Iris). A new profile defaults to Light/Neutral, regardless of OS theme. The preference is kept outside the task database in `$XDG_CONFIG_HOME/goreecloud-tasks/appearance.json` (or `~/.config/goreecloud-tasks/appearance.json`), in a private user-local file, and is not part of portable JSON backups. See [GC UI appearance notes](../docs/GC_UI_APPEARANCE_MIGRATION.md).

The GTK interface now offers Inbox/Today/Upcoming/Completed/Trash sidebar navigation and project shortcuts with live open-task counts. The top-bar Add Task control expands/collapses the composer, Ctrl+N opens capture, and Ctrl+F focuses Search. Settings groups appearance and guarded JSON backup tools; bulk tools appear only after selection. At native widths below 700 pixels, libadwaita collapses the sidebar and places View/Project routing in the Browse menu so tasks remain accessible. Its existing task data and JSON backup behavior are unchanged; see [native list-first UI](../docs/NATIVE_LIST_FIRST_UI.md). Native real-display accessibility and varying scale factors still require acceptance.

## Known limitations

The source installer has not undergone multi-distribution packaging tests, release signing, accessibility-device acceptance or update/rollback validation. Full Linux support and Stable acceptance remain pending.

**Task descriptions:** Native capture/edit accepts optional plain-text notes up to 2,000 UTF-16 code units. Active and deleted local SQLite tables gain an additive default-empty column, and recoverable Trash preserves it. JSON schema 2 is used whenever active tasks contain notes; schema-1 import remains supported. Older schema-1-only clients cannot import schema-2 notes; see [versioned compatibility rules](../docs/PORTABLE_SCHEMA2_DESCRIPTIONS.md).
