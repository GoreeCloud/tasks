# Offline outbox prototype — GoreeCloud Tasks

**Status: experimental reference module; not deployed or connected to clients.**

The accompanying `server/outbox.py` is an isolated reference component for a future offline synchronization client. It has no network access, stores no tokens, and is not called by the browser, native Linux app, native Android app, or the experimental loopback server. The `server/` location allows the current GitHub `api` CI job to pick up `server/tests/test_outbox.py` automatically; move it to a shared sync package when native-client integration is designed.

## What is implemented

- A private-permission SQLite database with WAL and transactional writes.
- Persistent mutation IDs to support idempotent retries after a crash or restart.
- Explicit conflict state that preserves the unsent mutation and a remote snapshot for future manual reconciliation.
- A remote server projection that does **not** overwrite local user edits.
- A change-feed cursor persisted in the same transaction as the applied page, with rejection of gaps, duplicate sequences and stale cursors.
- Conditional origin-mutation acknowledgement for matching single-user edit/delete events; rejection of forged or inconsistent operation/revision metadata.
- One-time initial snapshot seeding, with atomic checkpoint and refusal to overwrite queued local work.
- Validation for canonical UUIDs, UTF-8 JSON payloads, 64 KiB mutation bounds, task revisions, tombstones, and page lengths.
- Synthetic tests for persistence, idempotency, malformed mutations, conflict retention, cursor rollback, snapshot isolation, symlink safety, and compatibility with the current persisted single-user API feed.

## Important limits

**Do not use this to synchronize real user data.** There is no identity, account/workspace authorization, encryption at rest, transport, token management, crash-safe coupling to any client task edit, conflict-resolution UI, or server acknowledgement verification. `acknowledge()` represents a local state transition and must not be called before a successful, authenticated server receipt is durably verified. This is not a complete multi-device synchronization solution.

The current experimental single-user server emits contiguous global change sequences. The outbox deliberately rejects sequence gaps. A future multi-tenant or filtered feed may have noncontiguous global sequences and requires an updated cursor contract and reworked tests before use. An experimental, authenticated `/v1/bootstrap` endpoint now returns a consistent single-user snapshot and cursor for up to 100 tasks. The outbox accepts one such snapshot only when its local queue and remote projection are empty. This is not wired to the native clients; true end-to-end reconciliation and multi-tenant authorization remain unimplemented.

### Retry/acknowledgement ordering

A synthetic loopback contract test now demonstrates persisted mutation IDs from
`OfflineOutbox.pending()` used as HTTP `Idempotency-Key` values for PATCH and
DELETE, with repeated requests returning one server event before the outbox is
acknowledged and the delta applied. This is test scaffolding, not a native
client transport or a recovery protocol.

**Prototyped origin correlation:** new loopback API change events now include
an optional `mutationId`. For a known pending task edit/deletion, the outbox
checks its task, operation and expected revision before acknowledging the
mutation in the same transaction as its remote projection and cursor. A
synthetic HTTP contract test covers a delta arriving **before** the client
receives the successful mutation response. Earlier historical events keep a
null origin after non-destructive SQLite migration; they are not invented or
auto-acknowledged. A real native client still needs secure event attribution,
crash-safe coupling to its own task database, reconciliation UI and lifecycle
handling. Never conceal or silently overwrite a conflict.

## Test and review

Run from the checked-out `GoreeCloud/tasks` repository:

```sh
python3 -m py_compile server/outbox.py
python3 -m unittest discover -s server/tests -v
```

The tests are synthetic, run with temporary SQLite databases, and do not access external networks or accounts. After integrating and verifying all CI jobs, add lifecycle and power-loss testing, concurrency under separate processes, model adapters, field-level conflicts, and security review before enabling any client synchronization.

## Source and intended destination

- `server/outbox.py` — reference implementation.
- `server/tests/test_outbox.py` — isolated integration-style unit tests.
- `docs/OFFLINE_OUTBOX_PROTOTYPE.md` — this document.

This module is tracked source only. Its presence in a repository does not establish runtime client integration, remote deployment, or stable-release acceptance.
