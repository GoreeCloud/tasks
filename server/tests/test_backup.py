import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app
from goreecloud_tasks.backup import backup, verify, main


def test_online_backup_is_consistent_and_non_overwriting(tmp_path):
    source = tmp_path / "main.sqlite3"
    target = tmp_path / "snapshot.sqlite3"
    token = "tests-secret-do-not-use-in-production-000012345"
    client = TestClient(create_app(str(source), token))
    headers = {"Authorization": "Bearer " + token}

    original = client.post("/api/v1/tasks", headers=headers, json={"title": "Before snapshot"}).json()
    backup(source, target)
    assert main(["verify", "--database", str(target)]) == 0
    verify(target)
    assert oct(target.stat().st_mode & 0o777) == "0o600"

    client.post("/api/v1/tasks", headers=headers, json={"title": "After snapshot"})
    snapshot = sqlite3.connect(target)
    try:
        assert snapshot.execute("SELECT title FROM tasks").fetchall() == [("Before snapshot",)]
        assert snapshot.execute("PRAGMA user_version").fetchone()[0] == 2
        assert snapshot.execute("SELECT COUNT(*) FROM change_events").fetchone()[0] == 1
    finally:
        snapshot.close()
    with pytest.raises(FileExistsError):
        backup(source, target)
    assert main(["backup", "--database", str(source), "--output", str(target)]) == 1
    assert client.get("/api/v1/tasks/" + original["id"], headers=headers).status_code == 200


def test_backup_rejects_missing_corrupt_and_symlink_source(tmp_path):
    unknown = tmp_path / "unknown.db"
    target = tmp_path / "out.sqlite"
    with pytest.raises(ValueError):
        backup(unknown, target)
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a sqlite database")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        verify(corrupt)
    symlink = tmp_path / "alias"
    symlink.symlink_to(corrupt)
    with pytest.raises(ValueError):
        backup(symlink, target)
    assert not target.exists()
