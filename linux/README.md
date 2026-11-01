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

The native GTK interface also exposes **Export JSON** and **Import JSON** file dialogs using the same guarded implementation. It also provides a native **Edit** dialog for task title, priority, due date and project; changes are validated and applied together without clearing completion history. Completion toggles are idempotent: repeating an already-completed state does not rewrite the original completion timestamp stored in portable backups.

**Import requires an empty task database** and validates the entire JSON snapshot before committing any records. It never replaces live records. Export refuses a missing SQLite database or existing output file, so it cannot silently provide an empty misleading backup. Test backup compatibility and verify real recovery before using it for important work. Android import/export is now implemented and a limited Android 16 native document-picker smoke test passed; comprehensive provider, completed-task, and release acceptance is still pending. File-dialog interactions require full platform-specific GUI acceptance beyond the initial smoke launch.

## GTK runtime smoke (optional)

On a Linux machine with GTK4, libadwaita, PyGObject and `xvfb-run` installed:

```sh
xvfb-run -a python3 linux/tests/gui_smoke.py
```

This exercises the actual native window, task edit dialog and SQLite persistence
using a **temporary XDG_DATA_HOME**. The same headless GTK4 test is run in
GitHub Actions on Ubuntu 24.04 so source commits cannot silently break GTK
startup or the tested edit flow. It never reads or writes the user's normal
Tasks database. The smoke test does not replace visual, keyboard-navigation,
accessibility or multi-distribution acceptance. The GC UI stylesheet uses
libadwaita's adaptive palette variables for light/dark themes; GTK CSS does
not support browser `@media` rules.

## Known limitations

The source installer has not undergone multi-distribution packaging tests, release signing, accessibility-device acceptance or update/rollback validation. Full Linux support and Stable acceptance remain pending.
