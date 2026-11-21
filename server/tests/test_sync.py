import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app

TOKEN = "development-tests-only-token-should-never-be-deployed-1234"
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def client(tmp_path):
    path = tmp_path / "tasks.db"
    return TestClient(create_app(str(path), TOKEN))


def test_append_only_changes_and_deletion_tombstone(client):
    assert client.get("/api/v1/sync/changes").status_code == 401
    empty = client.get("/api/v1/sync/bootstrap", headers=AUTH).json()
    assert empty == {"format": "goreecloud-tasks-sync-1", "cursor": 0, "tasks": [], "projects": []}

    project = client.post("/api/v1/projects", headers=AUTH, json={"name": "Alpha"}).json()
    task = client.post("/api/v1/tasks", headers=AUTH,
                       json={"title": "One", "project_id": project["id"]}).json()
    patch = client.patch("/api/v1/tasks/" + task["id"], headers=AUTH,
                         json={"expected_version": 1, "title": "Two"})
    assert patch.status_code == 200
    deleted = client.delete("/api/v1/tasks/" + task["id"] + "?expected_version=2", headers=AUTH)
    assert deleted.status_code == 204

    first_page = client.get("/api/v1/sync/changes?after=0&limit=2", headers=AUTH).json()
    assert first_page["has_more"] is True
    assert first_page["next_cursor"] == 2
    assert [c["operation"] for c in first_page["changes"]] == ["upsert", "delete"]
    assert first_page["changes"][1]["payload"] is None

    second_page = client.get("/api/v1/sync/changes?after=2&limit=2", headers=AUTH).json()
    assert second_page["has_more"] is False
    assert [c["operation"] for c in second_page["changes"]] == ["delete", "delete"]
    assert second_page["changes"][1]["entity_id"] == task["id"]
    assert second_page["changes"][1]["payload"] is None
    assert second_page["next_cursor"] == 4

    bootstrap = client.get("/api/v1/sync/bootstrap", headers=AUTH).json()
    assert bootstrap["cursor"] == 4
    assert bootstrap["projects"][0]["id"] == project["id"]
    assert bootstrap["tasks"] == []
    assert client.get("/api/v1/sync/changes?after=4", headers=AUTH).json()["changes"] == []
    assert client.get("/api/v1/sync/changes?after=-1", headers=AUTH).status_code == 422


def test_idempotency_across_retries_and_conflicting_payload(client):
    key = "offline-device-create-001"
    headers = {**AUTH, "Idempotency-Key": key}
    body = {"title": "Do laundry", "due_date": "2026-11-30", "recurrence": "monthly"}
    first = client.post("/api/v1/tasks", json=body, headers=headers)
    retry = client.post("/api/v1/tasks", json=body, headers=headers)
    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json()
    assert len(client.get("/api/v1/tasks", headers=AUTH).json()) == 1

    conflict = client.post("/api/v1/tasks", json={"title": "A different task"}, headers=headers)
    assert conflict.status_code == 409
    cross_scope = client.post("/api/v1/projects", json={"name": "P"}, headers=headers)
    assert cross_scope.status_code == 409

    task = first.json()
    complete_key = {**AUTH, "Idempotency-Key": "offline-device-complete-002"}
    completed = client.post("/api/v1/tasks/" + task["id"] + "/complete",
                            json={"expected_version": 1}, headers=complete_key)
    completed_retry = client.post("/api/v1/tasks/" + task["id"] + "/complete",
                                  json={"expected_version": 1}, headers=complete_key)
    assert completed.status_code == completed_retry.status_code == 200
    assert completed.json() == completed_retry.json()
    assert completed.json()["next_task"]["due_date"] == "2026-12-30"
    assert len(client.get("/api/v1/tasks?status=all", headers=AUTH).json()) == 2
    assert client.post("/api/v1/tasks/" + task["id"] + "/complete",
                       json={"expected_version": 1}, headers=AUTH).status_code == 409
    events = client.get("/api/v1/sync/changes", headers=AUTH).json()["changes"]
    assert len(events) == 3, "One create + one completed + one recurring successor"


def test_project_idempotency_and_reopen_event(client):
    headers = {**AUTH, "Idempotency-Key": "project-create-123"}
    first = client.post("/api/v1/projects", headers=headers, json={"name": "Home"})
    second = client.post("/api/v1/projects", headers=headers, json={"name": "Home"})
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    t = client.post("/api/v1/tasks", headers=AUTH, json={"title": "Task"}).json()
    assert client.post("/api/v1/tasks/" + t["id"] + "/complete",
                       json={"expected_version": 1}, headers=AUTH).status_code == 200
    assert client.post("/api/v1/tasks/" + t["id"] + "/reopen",
                       json={"expected_version": 2}, headers=AUTH).status_code == 200
    events = client.get("/api/v1/sync/changes", headers=AUTH).json()["changes"]
    assert [(e["entity"], e["operation"]) for e in events] == [
        ("project", "upsert"), ("task", "upsert"), ("task", "upsert"), ("task", "upsert")
    ]


def test_concurrent_task_update_must_not_lose_revision(tmp_path):
    client = TestClient(create_app(str(tmp_path / "tasks.db"), TOKEN))
    created = client.post("/api/v1/tasks", headers=AUTH, json={"title": "Shared"}).json()
    barrier = Barrier(2)

    def update(title):
        barrier.wait(timeout=5)
        return client.patch("/api/v1/tasks/" + created["id"], headers=AUTH,
                            json={"expected_version": 1, "title": title})

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(update, "First")
        second = pool.submit(update, "Second")
        results = [first.result(timeout=15), second.result(timeout=15)]
    assert sorted(x.status_code for x in results) == [200, 409]
    final = client.get("/api/v1/tasks/" + created["id"], headers=AUTH).json()
    assert final["version"] == 2
    assert len(client.get("/api/v1/sync/changes", headers=AUTH).json()["changes"]) == 2


def test_v1_migration_preserves_existing_task(tmp_path):
    dbfile = tmp_path / "existing.sqlite3"
    old = TestClient(create_app(str(dbfile), TOKEN))
    task = old.post("/api/v1/tasks", headers=AUTH, json={"title": "Preserve"}).json()
    with sqlite3.connect(dbfile) as conn:
        conn.execute("DROP TABLE change_events")
        conn.execute("DROP TABLE request_receipts")
        conn.execute("PRAGMA user_version=1")
    updated = TestClient(create_app(str(dbfile), TOKEN))
    result = updated.get("/api/v1/sync/bootstrap", headers=AUTH).json()
    assert result["cursor"] == 0
    assert result["tasks"][0]["id"] == task["id"]
    with sqlite3.connect(dbfile) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3


def test_stable_pagination(client):
    for title in ["A", "B", "C"]:
        client.post("/api/v1/tasks", headers=AUTH, json={"title": title})
    first = client.get("/api/v1/tasks?limit=2", headers=AUTH).json()
    second = client.get("/api/v1/tasks?limit=2&offset=2", headers=AUTH).json()
    assert len(first) == 2 and len(second) == 1
    assert len({x["id"] for x in first + second}) == 3
    assert client.get("/api/v1/tasks?limit=1001", headers=AUTH).status_code == 422


def test_erased_task_scrubs_event_payloads_and_retry_receipts(client):
    key = "sensitive-create-1234"
    headers = {**AUTH, "Idempotency-Key": key}
    body = {"title": "Private task title", "description": "Private notes for deletion"}
    task = client.post("/api/v1/tasks", headers=headers, json=body).json()
    client.patch("/api/v1/tasks/" + task["id"], headers=AUTH,
                 json={"expected_version": 1, "description": "Updated secret notes"})
    assert client.delete("/api/v1/tasks/" + task["id"] + "?expected_version=2",
                         headers=AUTH).status_code == 204
    changes = client.get("/api/v1/sync/changes", headers=AUTH).json()["changes"]
    assert len(changes) == 3
    assert all(row["operation"] == "delete" and row["payload"] is None for row in changes)
    assert all(row["entity_id"] == task["id"] for row in changes)
    assert client.post("/api/v1/tasks", headers=headers, json=body).status_code == 410
    assert client.get("/api/v1/tasks?status=all", headers=AUTH).json() == []
