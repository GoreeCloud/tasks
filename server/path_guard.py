"""Fail closed on existing symlinked ancestors of local Tasks SQLite stores.

This checks the intended path before/after creating parents. It does not
protect against hostile concurrent directory renames; production deployments
must isolate writable directories or use descriptor-relative traversal.
"""
from __future__ import annotations

from pathlib import Path
import stat


def ensure_private_store_parent(path: Path) -> None:
    """Create missing parents (0700) but never traverse a linked ancestor."""
    parent = path.parent
    ancestors = tuple(reversed((parent, *parent.parents)))
    for ancestor in ancestors:
        try:
            mode = ancestor.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(mode):
            raise ValueError("SQLite store ancestry must contain only real directories")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Re-check immediately after creation; a static check is not race-proof.
    for ancestor in ancestors:
        if not stat.S_ISDIR(ancestor.lstat().st_mode):
            raise ValueError("SQLite store ancestry must contain only real directories")
