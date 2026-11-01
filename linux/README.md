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

The database at `$XDG_DATA_HOME/goreecloud-tasks/tasks.sqlite3` is intentionally **preserved on uninstall**. To delete task data, an explicit separate user action is required. Uninstall is not proof of data backup. There are no automatic updates or signing guarantees yet.

## Known limitations

The source installer has not undergone multi-distribution packaging tests, release signing, accessibility-device acceptance or update/rollback validation. Full Linux support and Stable acceptance remain pending.
