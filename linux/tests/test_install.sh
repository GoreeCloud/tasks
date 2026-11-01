#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
TEMP=$(mktemp -d)
trap 'rm -rf "$TEMP"' EXIT
export HOME="$TEMP/home"
export XDG_DATA_HOME="$TEMP/data"
export GC_TASKS_BIN_DIR="$TEMP/bin"
mkdir -p "$HOME" "$XDG_DATA_HOME/goreecloud-tasks"
printf 'KEEP-MY-TASKS' > "$XDG_DATA_HOME/goreecloud-tasks/tasks.sqlite3"
sh "$ROOT/linux/install.sh"
test -f "$XDG_DATA_HOME/applications/com.goreecloud.tasks.desktop"
test -x "$GC_TASKS_BIN_DIR/goreecloud-tasks"
test -f "$XDG_DATA_HOME/goreecloud-tasks/application/backup.py"
test -f "$XDG_DATA_HOME/goreecloud-tasks/application/theme.py"
test -f "$XDG_DATA_HOME/icons/hicolor/scalable/apps/com.goreecloud.tasks.svg"
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$XDG_DATA_HOME/applications/com.goreecloud.tasks.desktop"
fi
sh "$ROOT/linux/uninstall.sh"
test ! -f "$GC_TASKS_BIN_DIR/goreecloud-tasks"
test ! -f "$XDG_DATA_HOME/goreecloud-tasks/application/theme.py"
test ! -f "$XDG_DATA_HOME/applications/com.goreecloud.tasks.desktop"
test "$(cat "$XDG_DATA_HOME/goreecloud-tasks/tasks.sqlite3")" = 'KEEP-MY-TASKS'
printf 'DO-NOT-OVERWRITE' > "$TEMP/protected"
ln -s "$TEMP/protected" "$GC_TASKS_BIN_DIR/goreecloud-tasks"
if sh "$ROOT/linux/install.sh" > "$TEMP/unexpected.log" 2>&1; then
    echo 'Installer unexpectedly overwrote a symlink' >&2; exit 1
fi
test "$(cat "$TEMP/protected")" = 'DO-NOT-OVERWRITE'
echo "LINUX_INSTALL_UNINSTALL_SMOKE_PASS"
