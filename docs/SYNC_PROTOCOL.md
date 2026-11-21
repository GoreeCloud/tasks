# GoreeCloud Tasks change-feed contract — development stage

**Owner:** Tasks API, SQLite schema v4. **Status:** tested API changefeed and web-only, opt-in encrypted manual queue for standalone task creates and title edits; *not* complete offline-device synchronization. Native clients have no encrypted local queue, and no client has automatic background replay or device identity.

## Snapshot and incremental feed

Every endpoint requires the usual single-user Authorization: Bearer token. No public feed exists.

- **GET /api/v1/sync/bootstrap**: A consistent read transaction returns format=goreecloud-tasks-sync-1, cursor, tasks and projects. Snapshot limit: 5,000 tasks and 5,000 projects; oversized snapshots return HTTP 413.
- **GET /api/v1/sync/changes?after=0&limit=100**: Returns format, after, next_cursor, has_more, and changes. A change includes monotonic integer cursor, entity (task/project), entity_id, operation (upsert/delete), payload (serialized object or null), created_at. The limit is 1–200, default 100. Follow next_cursor until has_more is false.
- Writes and change events commit together. Project creation, task creation/edit/completion/reopen/deletion and recurring successor creation are represented. Task ordering is not a permanent stream index.
- On task deletion, earlier change payloads for the erased task are **redacted in place**, and past events become tombstones. This preserves personal data erasure rather than preserving an immutable history. Clients must apply repeated delete operations idempotently and not depend on erased historical payloads.
- v1 schema upgrades preserve current tasks but do not manufacture historic feed events. A newly connecting client must bootstrap before polling. Events are retained indefinitely until a validated retention/compaction protocol exists, except privacy redaction on deletion.

## Idempotent mutation retries

Optional Idempotency-Key header (8–128 characters; ASCII letters, digits, dot, underscore, tilde, hyphen) is supported on POST /projects, POST /tasks, PATCH /tasks/{id}, and POST /tasks/{id}/complete. With the same route and JSON content, a repeated key returns the stored response without duplicate creation or recurrence. A different route or payload with the same key returns HTTP 409. Erasure scrubs affected receipt responses; repeating a deleted task's original create/complete operation with its key returns HTTP 410 rather than resurrecting data. Receipts are not currently pruned automatically.

PATCH, DELETE and reopen still require expected_version. PATCH also supports an opt-in stable idempotency key to replay an acknowledged update when an HTTP response is lost; a different payload/task using the same key returns 409, and a deleted task's old receipt becomes 410. Mutations acquire SQLite BEGIN IMMEDIATE before loading the expected revision. Concurrent writers sharing a revision cannot both overwrite a task: one succeeds, one receives HTTP 409.

## Web-only encrypted manual queue — development stage

The optional React Offline view saves encrypted snapshots and bounded create/title-edit drafts in IndexedDB using a PBKDF2-derived AES-GCM key, protected by a user passphrase. Sync now sends creates with stable Idempotency-Key values and edits with the original expected_version; HTTP conflicts stop replay and require manual action. The web vault can now manually pull up to 10 pages of 200 changefeed records into a single authenticated, encrypted cache update, including deletion tombstones and cursor checks. This does **not** provide continuous multi-device background synchronization, compaction, or native clients. See OFFLINE_WEB.md for supported workflow, privacy and limitations.

## Remaining offline roadmap — not implemented

A future client must securely store a per-device identity and encrypted local cache; persist original idempotency keys through restarts; reconcile cursors and deletion tombstones; expose deterministic conflict resolution UI; support bounded snapshots/pagination, schema negotiation and compaction; enforce Identity subject scopes, GoreeShield consent/retention and Wardveil security requirements; and test loss, delays, clock skew, crashes, deletion and recovery. GoreeCloud Mesh must not publish task details to other products without separately verified authorization.

The change feed is a contract for future offline sync—not a guarantee of offline mutation support or production service readiness.
