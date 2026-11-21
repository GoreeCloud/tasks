"""Generate a development-only XDG desktop entry; never install automatically.

Requires an existing Python/PySide6 environment and adjacent Main.qml.
No API token, hostname, credential or unapproved brand icon is recorded.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def quote_exec_path(value: str) -> str:
    """Escape a full Exec argument under the Desktop Entry specification."""
    if not value or any(ord(character) < 32 or ord(character) == 127
                        for character in value):
        raise ValueError("Desktop entry executable paths cannot contain controls")
    # Percent is a field code even in double quotes. Other escapes follow
    # Desktop Entry Exec syntax; the original path is never executed by a shell.
    sanitized = (value.replace("%", "%%").replace("\\", "\\\\")
                 .replace('"', '\\"').replace("$", "\\$")
                 .replace(chr(96), "\\" + chr(96)))
    return '"' + sanitized + '"'


def create_entry(source_root: Path, python_path: Path) -> str:
    source = source_root.resolve(strict=True)
    main = source / "main.py"
    qml = source / "Main.qml"
    python = python_path.resolve(strict=True)
    if (not main.is_file() or not qml.is_file()
            or main.is_symlink() or qml.is_symlink()):
        raise ValueError("Trusted Linux Tasks main.py and Main.qml are required")
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError("Python executable must be a runnable file")
    command = quote_exec_path(str(python)) + " " + quote_exec_path(str(main))
    return (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        "Name=GoreeCloud Tasks (Development Preview)\n"
        "GenericName=Personal task manager\n"
        "Comment=Self-hosted single-user Tasks development client\n"
        "Categories=Office;Utility;\n"
        "Terminal=false\n"
        "StartupNotify=true\n"
        "Exec=" + command + "\n"
    )


def create_new_file(output: Path, contents: str) -> None:
    """Write a user-selected new file, without following a final symlink."""
    if not output.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(output, flags, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(contents)
    except BaseException:
        # Only clean up a newly created file, never overwrite a user's file.
        output.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate an uninstalled GoreeCloud Tasks development .desktop file"
    )
    parser.add_argument("--output", type=Path, required=True,
                        help="Path of a NEW .desktop file; never overwritten")
    parser.add_argument("--python", type=Path, default=Path(sys.executable),
                        help="Existing Python executable with PySide6 6.12.0")
    parser.add_argument("--linux-source", type=Path, default=Path(__file__).parent,
                        help="Folder containing the trusted main.py and Main.qml")
    args = parser.parse_args(argv)
    if args.output.suffix != ".desktop":
        parser.error("Output must use a .desktop extension")
    try:
        contents = create_entry(args.linux_source, args.python)
        create_new_file(args.output, contents)
    except (ValueError, OSError) as error:
        parser.exit(2, "Launcher generation refused: " + str(error) + "\n")
    print("Wrote uninstalled development desktop entry:", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
