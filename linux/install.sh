#!/bin/sh
# Installs a source-based native GTK4 GoreeCloud Tasks launcher for this user only.
set -eu
SOURCE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_DIR=${GC_TASKS_BIN_DIR:-"$HOME/.local/bin"}
APP_DIR="$DATA_HOME/goreecloud-tasks/application"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
LAUNCHER="$BIN_DIR/goreecloud-tasks"
DESKTOP_FILE="$DESKTOP_DIR/com.goreecloud.tasks.desktop"

# Reject ambiguous paths rather than writing a corrupt desktop Exec entry.
case "$BIN_DIR" in *[\"\`\\\$]*)
    echo "Unsupported launcher directory characters" >&2; exit 1 ;;
esac
if [ -L "$APP_DIR" ] || [ -L "$LAUNCHER" ] || [ -L "$DESKTOP_FILE" ] || [ -L "$ICON_DIR/com.goreecloud.tasks.svg" ]; then
    echo "Refusing to overwrite symlinked application paths" >&2
    exit 1
fi
if [ -e "$LAUNCHER" ] && ! grep -q '^# GoreeCloud Tasks launcher$' "$LAUNCHER"; then
    echo "An unrelated launcher already exists at $LAUNCHER" >&2
    exit 1
fi
if [ -e "$DESKTOP_FILE" ] && ! grep -q '^# GoreeCloud Tasks desktop entry$' "$DESKTOP_FILE"; then
    echo "An unrelated desktop entry already exists" >&2
    exit 1
fi

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
for file in app.py store.py style.css; do
    if [ -L "$APP_DIR/$file" ]; then echo "Refusing linked application file: $file" >&2; exit 1; fi
done
install -m 0644 "$SOURCE_DIR/app.py" "$SOURCE_DIR/store.py" "$SOURCE_DIR/style.css" "$APP_DIR/"
install -m 0644 "$SOURCE_DIR/assets/com.goreecloud.tasks.svg" "$ICON_DIR/com.goreecloud.tasks.svg"
cat > "$LAUNCHER" <<'EOF'
#!/bin/sh
# GoreeCloud Tasks launcher
set -eu
exec python3 "${XDG_DATA_HOME:-"$HOME/.local/share"}/goreecloud-tasks/application/app.py" "$@"
EOF
chmod 0755 "$LAUNCHER"
cat > "$DESKTOP_FILE" <<EOF
# GoreeCloud Tasks desktop entry
[Desktop Entry]
Type=Application
Name=GoreeCloud Tasks
Comment=Native, offline task management
Exec="$LAUNCHER"
Icon=com.goreecloud.tasks
Terminal=false
Categories=Office;
StartupNotify=true
EOF
chmod 0644 "$DESKTOP_FILE"
echo "Installed GoreeCloud Tasks launcher at $LAUNCHER"
echo "This does not install GTK/libadwaita system dependencies or configure updates."
echo "Local task data remains under $DATA_HOME/goreecloud-tasks/tasks.sqlite3"
