#!/bin/sh
# Removes only GoreeCloud Tasks application files; preserves tasks.sqlite3.
set -eu
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_DIR=${GC_TASKS_BIN_DIR:-"$HOME/.local/bin"}
APP_DIR="$DATA_HOME/goreecloud-tasks/application"
LAUNCHER="$BIN_DIR/goreecloud-tasks"
DESKTOP_FILE="$DATA_HOME/applications/com.goreecloud.tasks.desktop"
ICON="$DATA_HOME/icons/hicolor/scalable/apps/com.goreecloud.tasks.svg"

if [ -f "$LAUNCHER" ] && grep -q '^# GoreeCloud Tasks launcher$' "$LAUNCHER"; then rm -f "$LAUNCHER"; fi
if [ -f "$DESKTOP_FILE" ] && grep -q '^# GoreeCloud Tasks desktop entry$' "$DESKTOP_FILE"; then rm -f "$DESKTOP_FILE"; fi
if [ -f "$APP_DIR/app.py" ] && grep -q 'native GTK4.*GoreeCloud Tasks' "$APP_DIR/app.py"; then
    rm -f "$APP_DIR/app.py" "$APP_DIR/store.py" "$APP_DIR/backup.py" "$APP_DIR/theme.py" "$APP_DIR/style.css"
    rmdir "$APP_DIR" 2>/dev/null || true
fi
if [ -f "$ICON" ] && grep -q 'GoreeCloud Tasks icon' "$ICON"; then rm -f "$ICON"; fi
echo "Uninstalled GoreeCloud Tasks application files."
echo "Preserved device-local database: $DATA_HOME/goreecloud-tasks/tasks.sqlite3"
