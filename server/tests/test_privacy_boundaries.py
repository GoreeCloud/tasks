"""Privacy defense-in-depth: private file creation, response headers and safe errors."""
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app, Store


TOKEN = "test-only-valid-private-token-not-for-real-use-1234"
AUTH = {"Authorization":"Bearer "+TOKEN}


def test_new_database_is_restrictively_created(tmp_path):
    directory=tmp_path/"new-owned-tasks-directory"
    path=directory/"owner.sqlite3"
    assert not directory.exists()
    app=create_app(str(path),TOKEN)
    assert app is not None
    assert directory.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600
    with Store(str(path)).open() as conn:
        assert conn.execute("PRAGMA secure_delete").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert TestClient(app).get("/healthz").status_code == 200


def test_existing_database_is_not_overwritten_or_repermissioned(tmp_path):
    path=tmp_path/"existing.sqlite3"
    old=TestClient(create_app(str(path),TOKEN))
    created=old.post("/api/v1/tasks",headers=AUTH,json={"title":"Old private task"})
    assert created.status_code==201
    os.chmod(path,0o640)  # Existing permissions are operator-owned; no implicit mutation.
    new=TestClient(create_app(str(path),TOKEN))
    assert path.stat().st_mode & 0o777 == 0o640
    assert new.get("/api/v1/tasks",headers=AUTH).json()[0]["id"]==created.json()["id"]


def test_symlinked_db_path_is_rejected(tmp_path):
    original=tmp_path/"source.sqlite3"
    create_app(str(original),TOKEN)
    alias=tmp_path/"db-alias"
    alias.symlink_to(original)
    with pytest.raises(RuntimeError,match="Symlinked"):
        create_app(str(alias),TOKEN)
    assert alias.is_symlink() and original.exists()


def test_private_responses_no_store_and_security_headers(tmp_path):
    client=TestClient(create_app(str(tmp_path/"file.sqlite3"),TOKEN))
    samples=[
        client.get("/api/v1/tasks",headers=AUTH),
        client.get("/api/v1/tasks"),
        client.get("/api/v1/tasks?limit=999999",headers=AUTH),
        client.post("/api/v1/tasks",headers=AUTH,json={"title":"Hello"}),
    ]
    assert [item.status_code for item in samples]==[200,401,422,201]
    for response in samples:
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_validation_redacts_private_input_and_max_content_length(tmp_path):
    client=TestClient(create_app(str(tmp_path/"db.sqlite3"),TOKEN))
    marker="CONFIDENTIAL_NO_ECHO"
    invalid=client.post("/api/v1/tasks",headers=AUTH,json={
        "title":"Private task","description":marker+"x"*17000
    })
    assert invalid.status_code==422
    assert marker not in invalid.text
    assert len(invalid.text)<300
    assert "Invalid API request" in invalid.json()["detail"]
    invalid_habit=client.post("/api/v1/habits",headers=AUTH,json={
        "name":marker+"z"*180
    })
    assert invalid_habit.status_code==422
    assert marker not in invalid_habit.text

    # Defense-in-depth Content-Length guard; a reverse proxy must separately
    # enforce chunked-body limits before production network exposure.
    huge=client.post("/api/v1/tasks",headers=AUTH,json={
        "title":"Should not exist","description":"q"*1_048_700
    })
    assert huge.status_code==413 and huge.headers["cache-control"]=="no-store"
    assert "Should not exist" not in huge.text
    assert client.get("/api/v1/tasks",headers=AUTH).json()==[]


def test_actual_streamed_body_bound_not_only_advertised_length(tmp_path):
    """A chunked/unknown-length request cannot bypass the one-megabyte gate."""
    client=TestClient(create_app(str(tmp_path/"stream.sqlite3"),TOKEN))

    # An iterable body is transported as a stream, not a prebuilt JSON upload.
    valid=b'{"title":"Streaming accepted"}'
    accepted=client.post("/api/v1/tasks",headers={**AUTH, "Content-Type":"application/json",
        "Transfer-Encoding":"chunked"},content=iter([valid[:8],valid[8:]]))
    assert accepted.status_code==201
    assert accepted.json()["title"]=="Streaming accepted"

    # A client may advertise a too-small Content-Length or send no length.
    # Actual streamed size must always be checked before API handlers run.
    prefix=b'{"title":"Do not create","description":"'
    huge=[prefix,b"q"*1_048_577,b'"}']
    for headers in [
        {**AUTH,"Transfer-Encoding":"chunked"},
        {**AUTH,"Content-Length":"32"},
    ]:
        too_large=client.post("/api/v1/tasks",headers=headers,content=iter(huge))
        assert too_large.status_code==413
        assert too_large.headers["cache-control"]=="no-store"
        assert too_large.headers["x-content-type-options"]=="nosniff"
        assert b"Do not create" not in too_large.content
    assert [row["title"] for row in client.get("/api/v1/tasks",headers=AUTH).json()] == [
        "Streaming accepted"
    ]


def test_invalid_advertised_body_length_fails_private(tmp_path):
    client=TestClient(create_app(str(tmp_path/"invalid-length.sqlite3"),TOKEN))
    res=client.post("/api/v1/tasks",
                    headers={**AUTH, "Content-Length":"unknown"},
                    content=b'{"title":"Do not create"}')
    assert res.status_code==413 and res.headers["cache-control"]=="no-store"
    assert client.get("/api/v1/tasks",headers=AUTH).json()==[]
