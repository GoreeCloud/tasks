"""Bounded, transport-injected initial-sync collector for the local Tasks prototype.

No sockets, credentials, TLS exceptions, client database migration or logging.
The caller owns an authorized transport and must convert an HTTP 409 response
from /v1/bootstrap-page to the marker exception SnapshotChanged. Never return
a partial bootstrap to consumers, and never mix pages across checkpoints.
"""
from __future__ import annotations

from typing import Callable

from outbox import (
    MAX_BOOTSTRAP_PAGES, MAX_BOOTSTRAP_TASKS, MAX_BOOTSTRAP_TOTAL_BYTES,
    MAX_PAGE_CHANGES, OfflineOutbox, OutboxError, StaleCursor,
    canonical_uuid, safe_json,
)


EXPECTED_PAGE_KEYS = frozenset(
    ("schemaVersion", "tasks", "checkpoint", "nextAfter", "hasMore", "limit")
)
EXPECTED_TASK_KEYS = frozenset(
    ("id", "title", "priority", "due", "completed", "revision",
     "createdAt", "updatedAt", "deleted")
)


class SnapshotChanged(Exception):
    """Authorized source reported a checkpoint conflict (HTTP 409)."""


def collect_and_seed(
    outbox: OfflineOutbox,
    fetch_page: Callable[..., dict],
    *,
    limit: int = MAX_PAGE_CHANGES,
    max_restarts: int = 2,
) -> int:
    """Collect complete source pages then atomically seed a pristine outbox.

    fetch_page(*, limit, after, checkpoint) must be an authenticated caller
    callback with a strict origin/account binding. It returns the parsed JSON
    from /v1/bootstrap-page, or raises SnapshotChanged for an HTTP 409 only.
    No callback implementation or credentials are supplied by this module.

    Source churn discards all received pages and restarts from scratch, up to
    max_restarts additional tries. Malformed/oversized responses fail
    immediately and never create a local projection. A fully collected set is
    committed only by OfflineOutbox.seed_bootstrap_pages().
    """
    if not isinstance(outbox, OfflineOutbox) or not callable(fetch_page):
        raise OutboxError("Collector requires an outbox and a trusted page fetcher")
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_CHANGES:
        raise OutboxError("Invalid bootstrap page limit")
    if type(max_restarts) is not int or not 0 <= max_restarts <= 3:
        raise OutboxError("Invalid bootstrap restart budget")

    for attempt in range(max_restarts + 1):
        pages: list[dict] = []
        after: str | None = None
        checkpoint: int | None = None
        total_bytes = 0
        task_count = 0
        last_id: str | None = None
        for _ in range(MAX_BOOTSTRAP_PAGES):
            try:
                page = fetch_page(limit=limit, after=after, checkpoint=checkpoint)
            except SnapshotChanged:
                # Never seed even a valid-looking partial set.
                break

            if (not isinstance(page, dict) or set(page) != EXPECTED_PAGE_KEYS
                    or type(page.get("schemaVersion")) is not int or page["schemaVersion"] != 1):
                raise OutboxError("Invalid bootstrap page schema")
            current = page.get("checkpoint")
            if type(current) is not int or not 0 <= current < 2**63:
                raise OutboxError("Invalid bootstrap checkpoint")
            if checkpoint is None:
                checkpoint = current
            elif current != checkpoint:
                raise OutboxError("Mixed bootstrap checkpoints")

            tasks = page.get("tasks")
            has_more = page.get("hasMore")
            if (type(page.get("limit")) is not int or page["limit"] != limit
                    or not isinstance(tasks, list) or len(tasks) > limit
                    or type(has_more) is not bool
                    or (has_more and len(tasks) != limit)):
                raise OutboxError("Malformed bounded bootstrap page")
            for task in tasks:
                if not isinstance(task, dict) or set(task) != EXPECTED_TASK_KEYS:
                    raise OutboxError("Unexpected task snapshot schema")
                raw = safe_json(task)
                task_id = canonical_uuid(task.get("id"))
                if last_id is not None and task_id <= last_id:
                    raise OutboxError("Repeated or unordered bootstrap task")
                last_id = task_id
                task_count += 1
                total_bytes += len(raw.encode("utf-8"))
                if task_count > MAX_BOOTSTRAP_TASKS or total_bytes > MAX_BOOTSTRAP_TOTAL_BYTES:
                    raise OutboxError("Bootstrap staging budget exceeded")

            next_after = page.get("nextAfter")
            if has_more:
                if not tasks or canonical_uuid(next_after) != last_id:
                    raise OutboxError("Missing or invalid bootstrap continuation")
            elif next_after is not None:
                raise OutboxError("Unexpected terminal bootstrap continuation")

            pages.append(page)
            if not has_more:
                return outbox.seed_bootstrap_pages(pages)
            after = next_after
        else:
            raise OutboxError("Bootstrap exceeds maximum page count")

        # A 409 invalidates this entire attempt. No attempt writes any rows.
        if attempt == max_restarts:
            raise StaleCursor("Bootstrap changed repeatedly; retry later")

    raise AssertionError("Unreachable bootstrap collector state")
