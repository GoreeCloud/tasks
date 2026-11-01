"""Device-local GoreeCloud UI preference contract for native Linux Tasks.

No task or backup data is read or modified. The first launch is Light/Neutral.
"""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

APPEARANCES = ("light", "dark")
ACCENTS = ("neutral", "lagoon", "moss", "ember", "ocean", "iris")

# GC UI app-local semantic snapshot, referenced by color role/on-color role.
PALETTES = {
    "neutral": (("#374151", "#ffffff", "#e5e7eb", "#111827"),
                ("#d1d5db", "#111827", "#374151", "#f9fafb")),
    "lagoon": (("#087c8d", "#ffffff", "#d1f4f5", "#07565d"),
               ("#89e1e9", "#003b43", "#1c4d57", "#c8fcff")),
    "moss": (("#3f744b", "#ffffff", "#d8f1d9", "#25542d"),
             ("#a6dfa9", "#224b2a", "#304e37", "#e8f8e9")),
    "ember": (("#ae4d3f", "#ffffff", "#ffe2d7", "#6e3024"),
              ("#ffc2ad", "#592a20", "#603c36", "#ffe9e0")),
    "ocean": (("#1d4ed8", "#ffffff", "#dbeafe", "#1e3a8a"),
              ("#93c5fd", "#172554", "#1e3a8a", "#dbeafe")),
    "iris": (("#5145d9", "#ffffff", "#e8e6ff", "#2c227c"),
             ("#c5bfff", "#241b66", "#39316b", "#ebe8ff")),
}


def normalize(appearance=None, accent=None):
    return {
        "appearance": appearance if appearance in APPEARANCES else "light",
        "accent": accent if accent in ACCENTS else "neutral",
    }


def path_for_preferences():
    directory = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return directory / "goreecloud-tasks" / "appearance.json"


def read_preferences(path=None):
    path = Path(path) if path is not None else path_for_preferences()
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        return normalize()
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as handle:
            content = handle.read(4097)
        if len(content) > 4096:
            return normalize()
        payload = json.loads(content.decode("utf-8"))
        if type(payload) is not dict:
            return normalize()
        return normalize(payload.get("appearance"), payload.get("accent"))
    except (OSError, ValueError, UnicodeError, TypeError):
        return normalize()


def write_preferences(appearance, accent, path=None):
    if appearance not in APPEARANCES or accent not in ACCENTS:
        raise ValueError("Invalid GoreeCloud appearance or accent")
    path = Path(path) if path is not None else path_for_preferences()
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Refusing symlinked appearance preferences")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("Unsafe appearance preferences directory")
    # Only this application's preference directory is permission-tightened.
    path.parent.chmod(0o700)
    payload = json.dumps({"appearance": appearance, "accent": accent}, separators=(",", ":"))
    filename = None
    try:
        with NamedTemporaryFile(mode="w", dir=path.parent, prefix=".appearance-",
                                suffix=".tmp", delete=False, encoding="utf-8") as handle:
            filename = Path(handle.name)
            filename.chmod(0o600)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise ValueError("Refusing symlinked appearance preferences")
        os.replace(filename, path)
        filename = None
    finally:
        if filename is not None:
            filename.unlink(missing_ok=True)


def semantic_css(appearance, accent):
    """Use paired accessible GC UI foreground/background values in GTK styles."""
    mode = normalize(appearance, accent)
    primary, foreground, container, on_container = PALETTES[mode["accent"]][
        1 if mode["appearance"] == "dark" else 0
    ]
    return (".title-1 { color: " + primary + "; font-weight:800; } "
            "button.suggested-action { background-color: " + primary + "; color: " + foreground +
            "; border-radius:12px; min-height:44px; } "
            "window .bulk-selected { background-color: " + container + "; color: " +
            on_container + "; }")
