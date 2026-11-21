"""CSV migrations: preview-first, atomic, authorized, retry-safe and explicit loss."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from goreecloud_tasks.app import create_app

TOKEN = "never-use-fixture-csv-token-in-production-abc123456789"
AUTH = {"Authorization": "Bearer " + TOKEN}
GENERIC = (
    'title,description,due_date,priority,tags,recurrence,parent_row\n'
    'Plan move,"Pack, and organize",2026-12-04,1,"home|moving",none,\n'
    'Book van,,2026-12-03,2,logistics,none,1\n'
    'Move boxes,,2026-12-04,3,,none,2\n'
)
TODOIST = (
    "TYPE,CONTENT,DESCRIPTION,PRIORITY,INDENT,DATE,DATE_LANG,TIMEZONE\n"
    "task,Root task,Private note,1,1,2026-11-30,en,UTC\n"
    "task,Nested task,,3,2,,en,\n"
    "note,Note content,,4,2,,en,\n"
)


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "tasks.sqlite3"), TOKEN))


def preview(client, text=GENERIC, fmt="generic", **other):
    return client.post("/api/v1/import/csv/preview", headers=AUTH,
                       json={"format":fmt, "csv_text":text, **other})


def commit(client, source, digest, key="source-csv-import-001"):
    return client.post(
        "/api/v1/import/csv",
        headers={**AUTH, "Idempotency-Key":key},
        json={**source, "checksum":digest}
    )


def test_generic_preview_import_idempotency_subtasks_and_changefeed(client):
    source={"format":"generic","csv_text":GENERIC}
    unauthorized=client.post("/api/v1/import/csv/preview",json=source)
    assert unauthorized.status_code==401
    result=preview(client)
    assert result.status_code==200, result.text
    assert result.headers["cache-control"]=="no-store"
    assert result.headers["x-content-type-options"]=="nosniff"
    data=result.json()
    assert data["count"]==3
    assert data["tasks"][1]["parent_index"]==0
    assert data["tasks"][2]["parent_index"]==1
    assert data["tasks"][0]["tags"]==["home","moving"]
    assert data["warnings"]==[]
    assert client.get("/api/v1/tasks",headers=AUTH).json()==[]

    committed=commit(client,source,data["checksum"])
    assert committed.status_code==201, committed.text
    assert committed.headers["cache-control"]=="no-store"
    assert committed.json()["count"]==3
    retry=commit(client,source,data["checksum"])
    assert retry.status_code==201 and retry.json()==committed.json()
    tasks=client.get("/api/v1/tasks?status=all",headers=AUTH).json()
    by_name={item["title"]:item for item in tasks}
    assert len(by_name)==3
    assert by_name["Plan move"]["priority"]==1
    assert by_name["Plan move"]["description"]=="Pack, and organize"
    assert by_name["Book van"]["parent_id"]==by_name["Plan move"]["id"]
    assert by_name["Move boxes"]["parent_id"]==by_name["Book van"]["id"]
    feed=client.get("/api/v1/sync/changes",headers=AUTH).json()["changes"]
    assert len(feed)==3
    assert {row["entity_id"] for row in feed}==set(committed.json()["ids"])

    altered=commit(client,{**source,"csv_text":GENERIC.replace("Move boxes","Move plants")},
                   data["checksum"])
    assert altered.status_code==409
    assert len(client.get("/api/v1/tasks",headers=AUTH).json())==3


def test_todoist_basic_tasks_supported_and_unsupported_fields_flagged(client):
    data=preview(client,TODOIST,"todoist").json()
    assert data["count"]==2
    assert data["tasks"][1]["parent_index"]==0
    assert data["tasks"][0]["due_date"]=="2026-11-30"
    assert any("Unmapped" in warning and "date_lang" in warning for warning in data["warnings"])
    assert any("Skipped 1 non-task note" in warning for warning in data["warnings"])
    imported=commit(client,{"format":"todoist","csv_text":TODOIST},data["checksum"])
    assert imported.status_code==201
    tasks=client.get("/api/v1/tasks?status=all",headers=AUTH).json()
    assert len(tasks)==2
    by_title={task["title"]:task for task in tasks}
    assert by_title["Root task"]["priority"]==1
    assert by_title["Nested task"]["parent_id"]==by_title["Root task"]["id"]


def test_non_iso_dates_unsupported_structure_and_flatten_warning(client):
    source="TYPE,CONTENT,PRIORITY,INDENT,DATE\n" \
           "task,Review notes,1,1,every Friday\n"
    response=preview(client,source,"todoist")
    assert response.status_code==422
    assert "date must use YYYY-MM-DD" in response.json()["detail"]

    bad="TYPE,CONTENT,INDENT\nsection,Home,1\ntask,Orphan,2\n"
    response=preview(client,bad,"todoist")
    assert response.status_code==422
    assert "no parent task" in response.json()["detail"]
    flat=preview(client,bad,"todoist",flatten_hierarchy=True)
    assert flat.status_code==200
    assert flat.json()["tasks"][0]["parent_index"] is None
    assert any("flattened" in w for w in flat.json()["warnings"])


def test_validation_prevents_partial_import_and_wrong_project(client):
    bad="title,priority\nValid task,2\nBad priority,6\n"
    assert preview(client,bad).status_code==422
    oversized="title,tags\nValid task," + "|".join("tag"+str(i) for i in range(13)) + "\n"
    assert preview(client,oversized).status_code==422
    assert client.get("/api/v1/tasks",headers=AUTH).json()==[]

    source={"format":"generic","csv_text":GENERIC,"project_id":"missing-project"}
    checked=preview(client,GENERIC,project_id="missing-project")
    assert checked.status_code==200
    result=commit(client,source,checked.json()["checksum"],key="project-missing-001")
    assert result.status_code==422
    assert client.get("/api/v1/tasks",headers=AUTH).json()==[]


def test_bad_csv_and_body_are_bounded(client):
    cases=[
        ("title\n" + "x"*241 + "\n",422),
        ("title,description\nabc,malformed,3\n",422),
        ("title,due_date\nabc,21/11/2026\n",422),
        ('title,description\n"unterminated\n',422),
        ("title\nabc\x00def\n",422),
        ("title,title\none,two\n",422),
        ("name\nitem\n",422),
        ("title\n"+"\n".join(f"Task {i}" for i in range(501))+"\n",413),
    ]
    for csv_text, status in cases:
        response = preview(client, csv_text)
        assert response.status_code == status, (
            status, response.status_code, response.text[:200]
        )
    secret_marker = "SENSITIVE_DO_NOT_ECHO"
    invalid_response = client.post("/api/v1/import/csv/preview",headers=AUTH,json={
        "format":"generic","csv_text":"title\n" + secret_marker + "x"*500001
    })
    assert invalid_response.status_code == 422
    assert secret_marker not in invalid_response.text
    assert len(invalid_response.text) < 300
    assert invalid_response.headers["cache-control"] == "no-store"


def test_idempotency_missing_header_and_concurrent_retries(tmp_path):
    client=TestClient(create_app(str(tmp_path/"db.sqlite3"),TOKEN))
    source={"format":"generic","csv_text":"title\nOne new task\n"}
    digest=preview(client,source["csv_text"]).json()["checksum"]
    assert client.post("/api/v1/import/csv",headers=AUTH,
                       json={**source,"checksum":digest}).status_code==422
    barrier=Barrier(2)
    def run():
        barrier.wait(timeout=7)
        return commit(client,source,digest,key="parallel-csv-import")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(run)
        b=pool.submit(run)
        results=[a.result(timeout=20),b.result(timeout=20)]
    assert all(item.status_code==201 for item in results)
    assert results[0].json()==results[1].json()
    assert len(client.get("/api/v1/tasks",headers=AUTH).json())==1
