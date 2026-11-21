"""Deterministic date-only recurrence acceptance, no reminders or RRULE."""
import pytest
from fastapi.testclient import TestClient

from goreecloud_tasks.app import create_app

TOKEN="synthetic-recurrence-only-not-for-deployment-000000000000"
AUTH={"Authorization":"Bearer "+TOKEN}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path/"recurrence.sqlite3"),TOKEN))


@pytest.mark.parametrize("due,repeat,expected",[
    ("2026-11-20","weekdays","2026-11-23"),  # Fri -> Mon
    ("2026-11-21","weekdays","2026-11-23"),  # Sat -> Mon
    ("2026-11-22","weekdays","2026-11-23"),  # Sun -> Mon
    ("2026-11-23","weekdays","2026-11-24"),  # Mon -> Tue
    ("2026-11-30","biweekly","2026-12-14"),
    ("2026-12-31","biweekly","2027-01-14"),
    ("2024-02-29","yearly","2025-02-28"),   # Leap day clamps
    ("2028-02-29","yearly","2029-02-28"),
    ("2026-12-31","yearly","2027-12-31"),
])
def test_extended_recurrence_creates_one_successor(client,due,repeat,expected):
    task=client.post("/api/v1/tasks",headers=AUTH,json={
        "title":"Synthetic recurring",
        "due_date":due,
        "recurrence":repeat,
        "tags":["test"],
        "description":"Only a fixture",
    })
    assert task.status_code==201,task.text
    original=task.json()
    key={"Idempotency-Key":"recur-"+repeat+"-"+due}
    first=client.post("/api/v1/tasks/"+original["id"]+"/complete",headers={**AUTH,**key},
                      json={"expected_version":1})
    assert first.status_code==200,first.text
    successor=first.json()["next_task"]
    assert successor["due_date"]==expected
    assert successor["recurrence"]==repeat
    assert successor["series_id"]==original["id"]
    assert successor["tags"]==["test"]
    assert successor["completed_at"] is None
    assert first.json()["completed"]["completed_at"] is not None
    assert successor["version"]==1
    # An interrupted client may retry without generating duplicate successors.
    replay=client.post("/api/v1/tasks/"+original["id"]+"/complete",headers={**AUTH,**key},
                       json={"expected_version":1})
    assert replay.status_code==200 and replay.json()==first.json()
    all_tasks=client.get("/api/v1/tasks?status=all",headers=AUTH).json()
    assert len(all_tasks)==2
    changes=client.get("/api/v1/sync/changes",headers=AUTH).json()["changes"]
    assert len(changes)==3
    assert changes[-1]["entity_id"]==original["id"]


@pytest.mark.parametrize("repeat",["weekdays","biweekly","yearly"])
def test_new_recurrence_requires_date_and_supports_versioned_edit(client,repeat):
    missing=client.post("/api/v1/tasks",headers=AUTH,json={
        "title":"No date","recurrence":repeat
    })
    assert missing.status_code==422
    original=client.post("/api/v1/tasks",headers=AUTH,json={
        "title":"Editable","due_date":"2026-11-20"
    })
    assert original.status_code==201
    changed=client.patch("/api/v1/tasks/"+original.json()["id"],headers=AUTH,
                         json={"expected_version":1,"recurrence":repeat})
    assert changed.status_code==200,changed.text
    assert changed.json()["recurrence"]==repeat
    stale=client.patch("/api/v1/tasks/"+original.json()["id"],headers=AUTH,
                       json={"expected_version":1,"recurrence":"monthly"})
    assert stale.status_code==409
