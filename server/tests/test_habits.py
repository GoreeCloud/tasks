import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from goreecloud_tasks.app import create_app

TOKEN = "development-test-fixture-token-only-never-production-abcde"
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "tasks.db"), TOKEN))


def test_habit_crud_and_daily_streak(client):
    assert client.get("/api/v1/habits").status_code == 401
    assert client.post("/api/v1/habits", json={"name": "Run"}).status_code == 401
    assert client.post("/api/v1/habits", headers=AUTH, json={"name": " "}).status_code == 422
    created = client.post("/api/v1/habits", headers=AUTH,
                          json={"name": "  Exercise  ", "description": "No external tracking"})
    assert created.status_code == 201
    habit = created.json()
    assert habit["name"] == "Exercise"
    assert habit["version"] == 1 and habit["total_checkins"] == 0
    assert client.get("/api/v1/habits?as_of=2026-11-21", headers=AUTH).json()[0]["current_streak"] == 0

    first = client.post("/api/v1/habits/" + habit["id"] + "/checkins", headers=AUTH,
                        json={"day": "2026-11-19", "expected_version": 1})
    assert first.status_code == 201 and first.json()["version"] == 2
    second = client.post("/api/v1/habits/" + habit["id"] + "/checkins", headers=AUTH,
                         json={"day": "2026-11-20", "expected_version": 2})
    assert second.status_code == 201 and second.json()["current_streak"] == 2

    current = client.get("/api/v1/habits?as_of=2026-11-21", headers=AUTH).json()[0]
    assert current["current_streak"] == 2
    assert current["checked_in_today"] is False
    assert current["total_checkins"] == 2
    assert client.get("/api/v1/habits/" + habit["id"] + "/checkins", headers=AUTH).json() == [
        "2026-11-20", "2026-11-19"
    ]

    undone = client.delete("/api/v1/habits/" + habit["id"] + "/checkins/2026-11-20?expected_version=3",
                           headers=AUTH)
    assert undone.status_code == 200
    assert undone.json()["version"] == 4
    assert undone.json()["current_streak"] == 1
    assert client.delete("/api/v1/habits/" + habit["id"] +
                         "/checkins/2026-11-20?expected_version=4", headers=AUTH).status_code == 404
    edited = client.patch("/api/v1/habits/" + habit["id"], headers=AUTH,
                          json={"expected_version": 4, "name": "Morning run"})
    assert edited.status_code == 200 and edited.json()["name"] == "Morning run"
    assert client.patch("/api/v1/habits/" + habit["id"], headers=AUTH,
                        json={"expected_version": 4, "name": "Stale"}).status_code == 409

    snapshot = client.get("/api/v1/export", headers=AUTH).json()
    assert snapshot["habits"][0]["name"] == "Morning run"
    assert len(snapshot["habit_checkins"]) == 1
    assert client.delete("/api/v1/habits/" + habit["id"] + "?expected_version=5",
                         headers=AUTH).status_code == 204
    assert client.get("/api/v1/habits", headers=AUTH).json() == []
    after = client.get("/api/v1/export", headers=AUTH).json()
    assert after["habits"] == [] and after["habit_checkins"] == []


def test_habit_rejects_invalid_dates_and_revision(client):
    habit = client.post("/api/v1/habits", headers=AUTH, json={"name": "Hydrate"}).json()
    url = "/api/v1/habits/" + habit["id"] + "/checkins"
    assert client.post(url, headers=AUTH,
                       json={"day": "invalid", "expected_version": 1}).status_code == 422
    assert client.post(url, headers=AUTH,
                       json={"day": "2035-01-01", "expected_version": 1}).status_code == 422
    first = client.post(url, headers=AUTH,
                        json={"day": "2026-11-19", "expected_version": 1})
    assert first.status_code == 201
    assert client.post(url, headers=AUTH,
                       json={"day": "2026-11-19", "expected_version": 2}).status_code == 409
    assert client.delete(url + "/2026-11-19?expected_version=1", headers=AUTH).status_code == 409
    assert client.get(url + "?limit=1001", headers=AUTH).status_code == 422


def test_habit_concurrent_checkins_same_revision(tmp_path):
    client = TestClient(create_app(str(tmp_path / "tasks.db"), TOKEN))
    habit = client.post("/api/v1/habits", headers=AUTH, json={"name": "Read"}).json()
    barrier = Barrier(2)

    def log(day):
        barrier.wait(timeout=4)
        return client.post("/api/v1/habits/" + habit["id"] + "/checkins", headers=AUTH,
                           json={"day": day, "expected_version": 1})

    with ThreadPoolExecutor(max_workers=2) as executor:
        a = executor.submit(log, "2026-11-20")
        b = executor.submit(log, "2026-11-19")
        results = [a.result(timeout=12), b.result(timeout=12)]
    assert sorted(item.status_code for item in results) == [201, 409]
    assert client.get("/api/v1/habits/" + habit["id"] + "/checkins",
                      headers=AUTH).json().__len__() == 1


def test_v3_migration_preserves_tasks(tmp_path):
    path = tmp_path / "v3.sqlite3"
    app = TestClient(create_app(str(path), TOKEN))
    task = app.post("/api/v1/tasks", headers=AUTH, json={"title": "Keep old task"}).json()
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE habit_checkins")
        db.execute("DROP TABLE habits")
        db.execute("PRAGMA user_version=3")
    updated = TestClient(create_app(str(path), TOKEN))
    assert updated.get("/api/v1/tasks/" + task["id"], headers=AUTH).json()["title"] == "Keep old task"
    assert updated.get("/api/v1/habits", headers=AUTH).json() == []
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4


def test_habit_list_pagination_and_today_as_of(client):
    for name in ["Stretch", "Read", "Hydrate"]:
        assert client.post("/api/v1/habits", headers=AUTH, json={"name": name}).status_code == 201
    one = client.get("/api/v1/habits?as_of=2026-11-20&limit=2", headers=AUTH).json()
    two = client.get("/api/v1/habits?as_of=2026-11-20&limit=2&offset=2", headers=AUTH).json()
    assert len(one)==2 and len(two)==1
    assert [x["name"] for x in one+two] == ["Hydrate","Read","Stretch"]
    assert client.get("/api/v1/habits?limit=101", headers=AUTH).status_code == 422


def test_habit_rename_and_notes_preserve_private_checkin_history(client):
    habit = client.post("/api/v1/habits", headers=AUTH,
                        json={"name": "Walk", "description": "Private original"}).json()
    item = client.post("/api/v1/habits/" + habit["id"] + "/checkins",
                       headers=AUTH,
                       json={"day": "2026-11-19", "expected_version": 1})
    assert item.status_code == 201 and item.json()["version"] == 2
    edited = client.patch("/api/v1/habits/" + habit["id"], headers=AUTH,
                          json={"expected_version": 2,
                                "name": "  Evening walk  ", "description": "Private revised"})
    assert edited.status_code == 200
    assert edited.json()["name"] == "Evening walk"
    assert edited.json()["description"] == "Private revised"
    assert edited.json()["version"] == 3 and edited.json()["total_checkins"] == 1
    assert client.get("/api/v1/habits/" + habit["id"] + "/checkins",
                      headers=AUTH).json() == ["2026-11-19"]
    assert client.patch("/api/v1/habits/" + habit["id"], headers=AUTH,
                        json={"expected_version": 2, "name": "Stale"}).status_code == 409
    assert client.patch("/api/v1/habits/" + habit["id"], headers=AUTH,
                        json={"expected_version": 3, "description": "x" * 16001}).status_code == 422
    after = client.get("/api/v1/habits", headers=AUTH).json()[0]
    assert after["name"] == "Evening walk"
    assert after["description"] == "Private revised"
    assert after["version"] == 3
    assert after["total_checkins"] == 1
