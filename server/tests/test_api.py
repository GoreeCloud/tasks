import pytest
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app


TOKEN = "some-long-development-token-just-for-the-tests-123456"


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "tasks.sqlite3"), TOKEN))


@pytest.fixture()
def headers():
    return {"Authorization": "Bearer " + TOKEN}


def test_auth_required(client, headers):
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/v1/tasks").status_code == 401
    assert client.get("/api/v1/tasks", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/v1/tasks", headers=headers).json() == []


def test_task_crud_and_conflict(client, headers):
    project = client.post("/api/v1/projects", headers=headers, json={"name": " Family "})
    assert project.status_code == 201
    pid = project.json()["id"]
    created = client.post("/api/v1/tasks", headers=headers,
                          json={"title": " Plan weekend ", "project_id": pid,
                                "priority": 1, "tags": ["Home", "home"]})
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Plan weekend" and task["tags"] == ["home"]
    assert len(client.get("/api/v1/tasks", headers=headers).json()) == 1
    changed = client.patch("/api/v1/tasks/" + task["id"], headers=headers,
                           json={"expected_version": 1, "title": "Book tickets"})
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    assert client.patch("/api/v1/tasks/" + task["id"], headers=headers,
                        json={"expected_version": 1, "title": "Stale"}).status_code == 409
    assert client.delete("/api/v1/tasks/" + task["id"] + "?expected_version=1",
                         headers=headers).status_code == 409
    assert client.delete("/api/v1/tasks/" + task["id"] + "?expected_version=2",
                         headers=headers).status_code == 204


def test_recurrence_and_reopen(client, headers):
    t = client.post("/api/v1/tasks", headers=headers,
                    json={"title": "Review", "due_date": "2026-11-30",
                          "recurrence": "monthly"}).json()
    result = client.post("/api/v1/tasks/" + t["id"] + "/complete",
                         headers=headers, json={"expected_version": 1})
    assert result.status_code == 200
    assert result.json()["next_task"]["due_date"] == "2026-12-30"
    assert len(client.get("/api/v1/tasks", headers=headers).json()) == 1
    assert client.post("/api/v1/tasks/" + t["id"] + "/complete",
                       headers=headers, json={"expected_version": 1}).status_code == 409
    reopened = client.post("/api/v1/tasks/" + t["id"] + "/reopen",
                           headers=headers, json={"expected_version": 2})
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None


def test_validation_and_missing_project(client, headers):
    assert client.post("/api/v1/tasks", headers=headers, json={"title": " "}).status_code == 422
    assert client.post("/api/v1/tasks", headers=headers,
                       json={"title": "Task", "priority": 8}).status_code == 422
    assert client.post("/api/v1/tasks", headers=headers,
                       json={"title": "Task", "recurrence": "daily"}).status_code == 422
    assert client.post("/api/v1/tasks", headers=headers,
                       json={"title": "Task", "project_id": "not-a-project"}).status_code == 422
    assert client.get("/api/v1/tasks/no-such-task", headers=headers).status_code == 404


def test_filters_and_export(client, headers):
    for title, date in [("Alpha", "2026-11-01"), ("Beta", "2027-01-01")]:
        assert client.post("/api/v1/tasks", headers=headers,
                           json={"title": title, "due_date": date}).status_code == 201
    results = client.get("/api/v1/tasks?search=alp&due_before=2026-12-01", headers=headers)
    assert [x["title"] for x in results.json()] == ["Alpha"]
    export = client.get("/api/v1/export", headers=headers).json()
    assert export["format"] == "goreecloud-tasks-1" and len(export["tasks"]) == 2


def test_secret_and_database_version(tmp_path):
    with pytest.raises(RuntimeError, match="32 characters"):
        create_app(str(tmp_path / "x.sqlite"), "short")
