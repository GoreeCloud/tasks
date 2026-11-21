import os
import sqlite3

import pytest
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app
from goreecloud_tasks.backup import backup, verify, verify_tasks_schema, restore_drill, main


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
        assert snapshot.execute("PRAGMA user_version").fetchone()[0] == 4
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


def test_backup_restore_drill_roundtrip_is_lossless_and_nonoverwriting(tmp_path):
    live = tmp_path / "live.sqlite3"
    snapshot = tmp_path / "snapshot.sqlite3"
    recovered = tmp_path / "recovered.sqlite3"
    token = "fixture-only-backup-restoration-token-000000000000"
    client = TestClient(create_app(str(live), token))
    auth = {"Authorization": "Bearer " + token}
    parent = client.post("/api/v1/tasks", headers=auth,
                         json={"title": "Recover parent", "description": "Private data"}).json()
    child = client.post("/api/v1/tasks", headers=auth,
                        json={"title": "Recover child", "parent_id": parent["id"]}).json()
    habit = client.post("/api/v1/habits", headers=auth, json={"name": "Daily reading"}).json()
    assert client.post("/api/v1/habits/" + habit["id"] + "/checkins", headers=auth,
                       json={"day": "2026-11-20", "expected_version": 1}).status_code == 201
    backup(live, snapshot)
    expected = verify_tasks_schema(snapshot)
    assert expected["tasks"] == 2 and expected["habits"] == 1
    assert expected["habit_checkins"] == 1
    assert main(["restore-drill", "--backup", str(snapshot), "--output", str(recovered)]) == 0
    assert restore_drill(snapshot, tmp_path / "second-recovered.sqlite3") == expected
    assert recovered.stat().st_mode & 0o777 == 0o600
    assert verify_tasks_schema(recovered) == expected
    with sqlite3.connect(recovered) as db:
        assert db.execute("SELECT parent_id FROM tasks WHERE id=?", (child["id"],)).fetchone()[0] == parent["id"]
        assert db.execute("SELECT description FROM tasks WHERE id=?", (parent["id"],)).fetchone()[0] == "Private data"
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
    # The source service is still writable and was never replaced.
    assert client.post("/api/v1/tasks", headers=auth, json={"title": "Still alive"}).status_code == 201
    assert verify_tasks_schema(live)["tasks"] == 3
    assert verify_tasks_schema(recovered)["tasks"] == 2

    with pytest.raises(FileExistsError):
        restore_drill(snapshot, recovered)
    assert main(["restore-drill", "--backup", str(snapshot), "--output", str(recovered)]) == 1
    assert verify_tasks_schema(recovered) == expected


def test_restore_rejects_wrong_schema_corrupt_sources_and_symlinks(tmp_path):
    wrong = tmp_path / "other.sqlite3"
    with sqlite3.connect(wrong) as conn:
        conn.execute("CREATE TABLE arbitrary(data TEXT)")
        conn.execute("PRAGMA user_version=4")
    with pytest.raises(ValueError, match="missing required"):
        restore_drill(wrong, tmp_path / "not-created.db")
    assert not (tmp_path / "not-created.db").exists()

    invalid = tmp_path / "garbage.db"
    invalid.write_bytes(b"not a database")
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        restore_drill(invalid, tmp_path / "not-created.db")
    assert not (tmp_path / "not-created.db").exists()

    alias = tmp_path / "alias.sqlite3"
    alias.symlink_to(wrong)
    with pytest.raises(ValueError):
        restore_drill(alias, tmp_path / "not-created.db")

    output_alias = tmp_path / "output-link"
    output_alias.symlink_to(wrong)
    with pytest.raises(FileExistsError):
        backup(wrong, output_alias)
    assert output_alias.is_symlink()
