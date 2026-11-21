"""Task PATCH retries: atomic, deletion-aware and conflict-preserving."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from fastapi.testclient import TestClient
from goreecloud_tasks.app import create_app

TOKEN="synthetic-only-patch-retry-token-000000000000"
AUTH={"Authorization":"Bearer "+TOKEN}


def create(client,title="Original"):
    result=client.post("/api/v1/tasks",headers=AUTH,json={"title":title})
    assert result.status_code==201
    return result.json()


def patch(client,task_id,payload,key):
    return client.patch("/api/v1/tasks/"+task_id,
        headers={**AUTH,"Idempotency-Key":key},json=payload)


def test_patch_replay_resends_first_response_without_version_increment(tmp_path):
    client=TestClient(create_app(str(tmp_path/"db.sqlite3"),TOKEN))
    task=create(client)
    key="patch-lost-response-retry"
    payload={"title":"Updated", "expected_version":1}
    first=patch(client,task["id"],payload,key)
    assert first.status_code==200,first.text
    assert first.json()["version"]==2
    replay=patch(client,task["id"],payload,key)
    assert replay.status_code==200 and replay.json()==first.json()
    active=client.get("/api/v1/tasks/"+task["id"],headers=AUTH).json()
    assert active["version"]==2 and active["title"]=="Updated"
    changes=client.get("/api/v1/sync/changes",headers=AUTH).json()["changes"]
    assert len(changes)==2


def test_patch_reuse_key_rejects_different_content_and_route(tmp_path):
    client=TestClient(create_app(str(tmp_path/"db.sqlite3"),TOKEN))
    a=create(client,"A")
    b=create(client,"B")
    key="patch-content-conflict"
    original={"expected_version":1,"title":"New A"}
    assert patch(client,a["id"],original,key).status_code==200
    assert patch(client,a["id"],{"expected_version":1,"title":"Different"},key).status_code==409
    assert patch(client,b["id"],original,key).status_code==409
    # A different idempotency key cannot override a newer version.
    assert patch(client,a["id"],original,"patch-new-key").status_code==409
    assert client.get("/api/v1/tasks/"+a["id"],headers=AUTH).json()["title"]=="New A"
    assert client.get("/api/v1/tasks/"+b["id"],headers=AUTH).json()["version"]==1


def test_erasing_task_prevents_receipt_replaying_private_content(tmp_path):
    client=TestClient(create_app(str(tmp_path/"db.sqlite3"),TOKEN))
    task=create(client)
    key="patch-deleted-task"
    payload={"expected_version":1,"description":"Private updated notes"}
    updated=patch(client,task["id"],payload,key)
    assert updated.status_code==200
    assert client.delete("/api/v1/tasks/"+task["id"]+"?expected_version=2",
                         headers=AUTH).status_code==204
    retry=patch(client,task["id"],payload,key)
    assert retry.status_code==410
    assert "Private updated notes" not in retry.text
    all_changes=client.get("/api/v1/sync/changes",headers=AUTH).json()["changes"]
    assert all("Private updated notes" not in str(event) for event in all_changes)


def test_parallel_same_key_patch_yields_one_write(tmp_path):
    client=TestClient(create_app(str(tmp_path/"db.sqlite3"),TOKEN))
    task=create(client)
    barrier=Barrier(2)
    key="parallel-edit-replay"
    def run():
        barrier.wait(timeout=8)
        return patch(client,task["id"],{"expected_version":1,"title":"One revised value"},key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(run);b=pool.submit(run)
        results=[a.result(timeout=18),b.result(timeout=18)]
    assert [r.status_code for r in results]==[200,200]
    assert results[0].json()==results[1].json()
    assert client.get("/api/v1/tasks/"+task["id"],headers=AUTH).json()["version"]==2
    changes=client.get("/api/v1/sync/changes",headers=AUTH).json()["changes"]
    assert len(changes)==2
