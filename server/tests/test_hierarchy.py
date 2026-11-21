"""Multi-level task hierarchy API acceptance: migration, invariants, events and erasure."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from goreecloud_tasks.app import create_app

TOKEN = "development-fixture-only-token-should-never-be-deployed-abcde"
HEADERS = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "tasks.sqlite3"), TOKEN))


def create(client, title, parent_id=None, **other):
    return client.post("/api/v1/tasks", headers=HEADERS,
                       json={"title": title, "parent_id": parent_id, **other})


def patch(client, task, **changes):
    return client.patch("/api/v1/tasks/" + task["id"], headers=HEADERS,
                        json={"expected_version": task["version"], **changes})


def test_nested_tasks_and_cycle_prevention(client):
    grandparent = create(client, "Plan trip").json()
    child = create(client, "Book flights", grandparent["id"]).json()
    grandchild = create(client, "Check passport", child["id"]).json()
    assert grandchild["parent_id"] == child["id"]
    assert [r["parent_id"] for r in client.get("/api/v1/tasks", headers=HEADERS).json()
            if r["id"] == child["id"]] == [grandparent["id"]]

    assert create(client, "Orphan", "not-a-real-task").status_code == 422
    assert patch(client, grandparent, parent_id=grandparent["id"]).status_code == 422
    assert patch(client, grandparent, parent_id=grandchild["id"]).status_code == 422
    assert patch(client, child, parent_id=grandchild["id"]).status_code == 422
    assert create(client, "Subtask", grandparent["id"]).status_code == 201

    assert client.get("/api/v1/sync/bootstrap", headers=HEADERS).json()["tasks"][0].get("parent_id") is not None or \
           all("parent_id" in task for task in client.get("/api/v1/sync/bootstrap", headers=HEADERS).json()["tasks"])


def test_completion_invariant_and_reopen(client):
    parent = create(client, "Parent").json()
    child = create(client, "Child", parent["id"]).json()
    subchild = create(client, "Grandchild", child["id"]).json()
    def complete(task):
        return client.post("/api/v1/tasks/" + task["id"] + "/complete",
                           headers=HEADERS, json={"expected_version": task["version"]})
    assert complete(parent).status_code == 409
    assert complete(child).status_code == 409
    assert complete(subchild).status_code == 200
    assert complete(child).status_code == 200
    assert complete(parent).status_code == 200
    assert create(client, "Under completed parent", parent["id"]).status_code == 409
    assert client.post("/api/v1/tasks/" + child["id"] + "/reopen", headers=HEADERS,
                       json={"expected_version": 2}).status_code == 409
    reopened_parent = client.post("/api/v1/tasks/" + parent["id"] + "/reopen",
                                 headers=HEADERS, json={"expected_version": 2})
    assert reopened_parent.status_code == 200
    assert client.post("/api/v1/tasks/" + child["id"] + "/reopen", headers=HEADERS,
                       json={"expected_version": 2}).status_code == 200


def test_parent_deletion_detaches_child_with_revision_and_feed(client):
    parent = create(client, "Parent task", description="Sensitive parent notes").json()
    child = create(client, "Child task", parent["id"]).json()
    before = client.get("/api/v1/sync/bootstrap", headers=HEADERS).json()["cursor"]
    deleted = client.delete("/api/v1/tasks/" + parent["id"] + "?expected_version=1", headers=HEADERS)
    assert deleted.status_code == 204
    current = client.get("/api/v1/tasks/" + child["id"], headers=HEADERS).json()
    assert current["parent_id"] is None
    assert current["version"] == 2
    changes = client.get("/api/v1/sync/changes?after=" + str(before), headers=HEADERS).json()["changes"]
    assert [(x["entity_id"], x["operation"]) for x in changes] == [
        (child["id"], "upsert"), (parent["id"], "delete")
    ]
    assert changes[0]["payload"]["parent_id"] is None
    all_changes = client.get("/api/v1/sync/changes", headers=HEADERS).json()["changes"]
    assert not any("Sensitive parent notes" in str(x) for x in all_changes)
    assert any(x["entity_id"] == parent["id"] and x["operation"] == "delete" for x in all_changes)


def test_parent_idempotency_and_parentless_recurring_successor(client):
    parent = create(client, "Parent recurring", due_date="2026-11-30", recurrence="monthly").json()
    child = create(client, "Child", parent["id"]).json()
    key = {**HEADERS, "Idempotency-Key": "child-create-idem-12345"}
    first = client.post("/api/v1/tasks", headers=key,
                        json={"title": "Dedupe", "parent_id": parent["id"]})
    retry = client.post("/api/v1/tasks", headers=key,
                        json={"title": "Dedupe", "parent_id": parent["id"]})
    assert first.status_code == retry.status_code == 201
    assert first.json() == retry.json()
    for sub in [child, first.json()]:
        assert client.post("/api/v1/tasks/" + sub["id"] + "/complete", headers=HEADERS,
                           json={"expected_version": 1}).status_code == 200
    completed = client.post("/api/v1/tasks/" + parent["id"] + "/complete",
                            headers=HEADERS, json={"expected_version": 1})
    assert completed.status_code == 200, completed.text
    assert completed.json()["next_task"]["parent_id"] is None


def test_v2_schema_upgrade_preserves_childless_tasks(tmp_path):
    dbfile = tmp_path / "upgrade.sqlite3"
    first = TestClient(create_app(str(dbfile), TOKEN))
    task = create(first, "Before migration").json()
    with sqlite3.connect(dbfile) as con:
        con.execute("PRAGMA user_version=2")
        con.execute("ALTER TABLE tasks RENAME TO tasks_before")
        con.execute("""CREATE TABLE tasks(
            id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
            project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
            due_date TEXT, priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 4),
            tags TEXT NOT NULL, recurrence TEXT NOT NULL, series_id TEXT,
            completed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1)""")
        con.execute("""INSERT INTO tasks(id,title,description,project_id,due_date,priority,
            tags,recurrence,series_id,completed_at,created_at,updated_at,version)
            SELECT id,title,description,project_id,due_date,priority,
            tags,recurrence,series_id,completed_at,created_at,updated_at,version
            FROM tasks_before""")
        con.execute("DROP TABLE tasks_before")
    upgraded = TestClient(create_app(str(dbfile), TOKEN))
    result = upgraded.get("/api/v1/tasks/" + task["id"], headers=HEADERS).json()
    assert result["parent_id"] is None
    with sqlite3.connect(dbfile) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 3
