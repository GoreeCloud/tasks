"""Atomic task change feed and optional idempotent create/complete receipts.

All helpers are called *inside* Store.transaction(), which acquires a SQLite
BEGIN IMMEDIATE writer lock before any optimistic-version read or receipt read.
This prevents duplicate retries and concurrent lost updates across workers.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from fastapi import HTTPException


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(scope: str, request_payload: dict) -> str:
    return hashlib.sha256((scope + "\n" + _json(request_payload)).encode("utf-8")).hexdigest()


def replay_receipt(conn: sqlite3.Connection, key: str | None,
                   scope: str, request_payload: dict) -> Any | None:
    """Return a committed prior response, or None if no receipt exists.

    A key cannot be reused for a different operation or payload, even if the
    operation is directed at another task or a different route.
    """
    if key is None:
        return None
    row = conn.execute(
        "SELECT scope, fingerprint, response_json FROM request_receipts WHERE idempotency_key=?",
        (key,),
    ).fetchone()
    if not row:
        return None
    if row["scope"] != scope or row["fingerprint"] != _fingerprint(scope, request_payload):
        raise HTTPException(status_code=409, detail="Idempotency-Key already used for another operation")
    response = json.loads(row["response_json"])
    if isinstance(response, dict) and response.get("_goreecloud_erased") is True:
        raise HTTPException(status_code=410, detail="Original task was deleted; retry is no longer replayable")
    return response


def save_receipt(conn: sqlite3.Connection, key: str | None, scope: str,
                 request_payload: dict, response: Any, created_at: str) -> None:
    if key is not None:
        conn.execute(
            """INSERT INTO request_receipts
               (idempotency_key,scope,fingerprint,response_json,created_at)
               VALUES (?,?,?,?,?)""",
            (key, scope, _fingerprint(scope, request_payload), _json(response), created_at),
        )


def record_change(conn: sqlite3.Connection, entity: str, entity_id: str,
                  operation: str, payload: dict | None, created_at: str) -> None:
    """Write an append-only upsert/tombstone in the same DB transaction."""
    conn.execute(
        """INSERT INTO change_events(entity,entity_id,operation,payload,created_at)
           VALUES(?,?,?,?,?)""",
        (entity, entity_id, operation, _json(payload) if payload is not None else None, created_at),
    )


def scrub_task_history(conn: sqlite3.Connection, task_id: str) -> None:
    """Privacy-preserving purge for a deleted task while retaining cursor order.

    Historical upserts become tombstones, and idempotency receipts that refer
    to the erased task become replay-blocking markers. This avoids both
    retaining deleted descriptions and recreating a task on a delayed retry.
    """
    conn.execute(
        """UPDATE change_events SET operation='delete', payload=NULL
           WHERE entity='task' AND entity_id=?""",
        (task_id,),
    )
    for row in conn.execute(
        "SELECT idempotency_key, response_json FROM request_receipts"
    ).fetchall():
        response = json.loads(row["response_json"])
        def refers_to_target(value: Any) -> bool:
            if isinstance(value, dict):
                if value.get("id") == task_id:
                    return True
                return any(refers_to_target(item) for item in value.values())
            if isinstance(value, list):
                return any(refers_to_target(item) for item in value)
            return False
        if refers_to_target(response):
            conn.execute(
                "UPDATE request_receipts SET response_json=? WHERE idempotency_key=?",
                ('{"_goreecloud_erased":true}', row["idempotency_key"]),
            )
