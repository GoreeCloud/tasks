"""Durable idempotency receipts for an experimental Tasks mutation protocol.

This helper has no network I/O. Its caller MUST use one SQLite IMMEDIATE
transaction for receipt lookup, task mutation, change event and receipt save.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from uuid import UUID

_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_ALLOWED = frozenset(("PATCH", "DELETE"))
_MAX_BODY_BYTES = 64 * 1024


class ReceiptError(ValueError):
    """Malformed mutation or idempotency key."""


class ReceiptConflict(ReceiptError):
    """A committed mutation key was reused for different content."""


def _object_json(value: object) -> str:
    if not isinstance(value, dict):
        raise ReceiptError("Mutation data must be an object")
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
        if len(raw.encode("utf-8")) > _MAX_BODY_BYTES:
            raise ReceiptError("Mutation data exceeds 64 KiB")
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ReceiptError("Mutation data is not valid UTF-8 JSON") from exc
    return raw


def fingerprint(method: str, task_id: str, revision: int,
                fields: dict | None) -> str:
    """Bind a retry to method, task, expected revision, and normalized fields."""
    if method not in _ALLOWED:
        raise ReceiptError("Unsupported mutation method")
    try:
        if str(UUID(task_id)) != task_id:
            raise ValueError("noncanonical UUID")
    except (TypeError, ValueError, AttributeError) as exc:
        raise ReceiptError("Expected canonical lowercase UUID task ID") from exc
    if type(revision) is not int or not 1 <= revision < 2**31:
        raise ReceiptError("Expected positive task revision")
    if method == "PATCH" and (fields is None or not isinstance(fields, dict) or not fields):
        raise ReceiptError("PATCH requires normalized fields")
    if method == "DELETE" and fields is not None:
        raise ReceiptError("DELETE cannot have a request body")
    canonical = _object_json({"method": method, "taskId": task_id,
                              "expectedRevision": revision, "fields": fields})
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class MutationReceipts:
    """Use an already opened SQLite connection; never commits independently."""

    @staticmethod
    def _key(key: str) -> None:
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise ReceiptError("Idempotency-Key must have 8–128 safe characters")

    @classmethod
    def lookup(cls, db: sqlite3.Connection, key: str, digest: str) -> dict | None:
        cls._key(key)
        row = db.execute(
            "SELECT payload_hash,response_json FROM idempotency WHERE request_key=?",
            (key,)
        ).fetchone()
        if row is None:
            return None
        if not hmac.compare_digest(row[0], digest):
            raise ReceiptConflict("Idempotency key already belongs to a different mutation")
        try:
            reply = json.loads(row[1])
        except (TypeError, ValueError) as exc:
            raise ReceiptError("Persisted receipt is corrupted") from exc
        if not isinstance(reply, dict):
            raise ReceiptError("Persisted receipt is not an object")
        return reply

    @classmethod
    def save(cls, db: sqlite3.Connection, key: str, digest: str,
             reply: dict) -> None:
        cls._key(key)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ReceiptError("Expected SHA-256 mutation fingerprint")
        raw = _object_json(reply)
        db.execute(
            "INSERT INTO idempotency(request_key,payload_hash,response_json) "
            "VALUES (?,?,?)", (key, digest, raw)
        )
