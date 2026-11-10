# GoreeCloud Tasks — Experimental Loopback API

**Status:** Implemented source prototype with automated tests; not a deployed, production-grade, multi-user, TLS-protected, supported native service. This development API must **not** be exposed on an external network.

## Purpose

This independent service foundation creates a contract for future authenticated task synchronization and native client interoperability. The first release remains **single-user** and intentionally separate from browser, Linux and Android local stores. None of those clients connect to it yet.

## Security properties implemented in source

- Binds exclusively to `127.0.0.1`; port configurable (default 3037).
- Refuses startup without `GOREETASKS_API_TOKEN` of at least 32 non-whitespace characters; never commits or logs the secret.
- All task/change endpoints require `Authorization: Bearer …`. Only `/healthz` is unauthenticated.
- No CORS response headers; browser cross-origin access is not enabled.
- Header ambiguity defense: reject repeated Authorization, Content-Length, Content-Type, If-Match and Idempotency-Key fields before mutation; reject Transfer-Encoding framing. No reverse proxy is provided, and this does not establish production request-smuggling resistance.
- Explicit JSON nesting limit (32 object/array levels), rejecting excessive depth before JSON decoding and before receipt or mutation persistence. Escaped JSON string contents do not contribute to nesting depth.
- Input validation and 64 KiB JSON request bounds; duplicate object field names (including escaped aliases) and nonstandard `NaN`/`Infinity` numeric constants are rejected before mutations or idempotency receipts. Unknown or differently cased task fields are rejected by the task schema. No unreviewed shell commands or executable payloads.
- Parameterized SQLite queries, transactions and WAL, private-directory permissions where supported.
- Idempotency-Key for task creation; conflicts on reused keys with divergent payloads.
- Optional, durable Idempotency-Key receipts for PATCH/DELETE, bound to method/task/revision/normalized fields, committed in the task and change-event transaction.
- Optimistic revision preconditions for task edits and deletion to prevent silent stale overwrites.
- Soft deletion with immutable, ordered change-log snapshots and cursor-based pagination (100 events per page).
- Optional originating `mutationId` in new change events; legacy events remain readable with null mutationId after a non-destructive schema upgrade.
- HTTP no-store/no-sniff headers. No request payloads, titles or tokens in the server's request log.

These controls are useful development foundations but **not** proof of production security, authorization completeness or stable synchronization. There is no account identity, workspace isolation, rate limiting, authentication rotation, data encryption at rest, reverse-proxy TLS, backend monitoring, migrations, or restore drills. No Internet binding or external publication is provided.

## Start a local development instance

Requires Python 3.10+ (standard library only). Run from repository root:

```sh
export GOREETASKS_API_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
python3 server/api.py --port 3037
```

Do not reuse production credentials or user task records. The server database defaults to a separate private XDG directory (`~/.local/share/goreecloud-tasks-server/` unless `XDG_DATA_HOME` is set), deliberately outside the native client databases. Database files are created with mode 0600 and obvious symlink paths are rejected. Ensure every custom `--database` directory is private as well, including its SQLite journal files. Environment-based token use is only a development control; deploy no public services from this script.

## API contract

Responses are JSON. Requests with bodies require `Content-Type: application/json`.

| Method | Path | Operation |
|---|---|---|
| GET | `/healthz` | Loopback-only health check |
| GET | `/v1/bootstrap` | Legacy authenticated, transactionally consistent active-task snapshot and change cursor (maximum 100 tasks) |
| GET | `/v1/bootstrap-page?limit=100` | Authenticated bounded keyset initial snapshot; continuation requires `after={nextAfter}&checkpoint={checkpoint}`; rejects concurrent workspace changes with HTTP 409 |
| GET | `/v1/tasks?limit=100` | Read up to 100 non-deleted tasks, including `hasMore` overflow signal |
| GET | `/v1/tasks/{id}` | Read a task |
| POST | `/v1/tasks` | Create a task; requires `Idempotency-Key` (8–128 safe characters) |
| PATCH | `/v1/tasks/{id}` | Update title, priority, due, completed; requires `If-Match` integer revision; `Idempotency-Key` strongly recommended for retries |
| DELETE | `/v1/tasks/{id}` | Tombstone task; requires `If-Match` revision; `Idempotency-Key` strongly recommended for retries |
| GET | `/v1/changes?after=0&limit=100` | Immutable ordered changes with cursor/hasMore |

### Authenticated 127.0.0.1 bootstrap integration (development only)

The new `server/loopback_bootstrap.py` provides `LoopbackBootstrapTransport(port, token).fetch_page(limit=..., after=..., checkpoint=...)`. When a **trusted local user** starts the experimental API on the same machine, this callback can be passed to `collect_and_seed()` with a freshly created, empty `OfflineOutbox`. Synthetic integration tests exercise real loopback HTTP without reading any user's existing Tasks stores.

The transport constructs its destination as `127.0.0.1` plus a validated numeric port. It cannot be configured with a DNS host, URI, reverse proxy, remote IP or redirect target; `http.client` makes a direct connection without environmental HTTP proxies and never follows Location headers. A developer-supplied ASCII bearer token is used in process memory only, not in URLs, logs, filenames, serialized snapshots, or default object representations. A token is **not** acquired, rotated, stored, shared across accounts or managed by this library.

Only authenticated HTTP 200 JSON with a single exact content type, content length, no-store cache policy, no Transfer-Encoding/content encoding, <=2 MiB body, strict UTF-8, unique JSON properties and legal numeric constants is accepted. HTTP 409 is mapped to `SnapshotChanged`, causing the collector to discard and restart incomplete sets. Unexpected HTTP statuses, 3xx redirects, short reads, duplicate framing, malformed responses, and failed authorization abort without committing task data. The collector still validates the exact snapshot schema and stages before the one-time outbox transaction.

**Security and release limits:** Loopback cleartext remains observable to privileged local software and is not a multi-user trust boundary. A malicious local listener or compromised host is outside this prototype's authenticated source assurance. There is no device installation, browser CORS, native app wiring, TLS, secure credential vault, Identity tenant authorization, GoreeShield sharing approval, Wardveil production ingress review, long-lived sync worker or remote service connection. Never expose the development port publicly or reuse production secrets. A future networked connector must be a separately reviewed implementation with authorized secure transport.

### Bounded bootstrap collection adapter (synthetic-only)

The new `server/bootstrap_client.py` provides `collect_and_seed(outbox, fetch_page, limit=100, max_restarts=2)`. This is a **transport-injected synchronous orchestration helper**, not a network client. The trusted caller must authenticate the intended source/account, validate TLS/identity as applicable, parse its JSON within HTTP response budgets, and implement `fetch_page(*, limit, after, checkpoint)`. Only HTTP **409** from the intended source should be mapped to the marker `SnapshotChanged`; all other authentication, protocol, transport, and authorization errors must propagate and must not be retried as stale checkpoints.

The collector gathers a full bounded sequence in memory, asks for each next page using the exact prior UUID cursor and unchanged high-water checkpoint, checks strict page shape/order, stages at most 1000 pages, 10,000 tasks, and 16 MiB of UTF-8 snapshots, and calls `OfflineOutbox.seed_bootstrap_pages()` **once** on successful terminal completion. On 409, it abandons the entire partial set and attempts a fresh checkpoint no more than two additional times by default; repeated churn fails without writing a projection. It never logs task titles, stores credentials, opens sockets, changes the native task databases, or claims that injected callbacks validate source authenticity. This is a foundation for a future independently authenticated and consented client connector, **not a deployed cloud synchronization feature**.

### Complete initial snapshot paging (development v1)

**Offline projection acceptance (source-only):** `OfflineOutbox.seed_bootstrap_pages(pages)` can now atomically seed a fresh local projection from a **fully collected** `/v1/bootstrap-page` response sequence. It validates schema/version, one identical checkpoint, bounded page sizes, terminal completion, cursor presence, canonical strictly increasing UUIDs, revisions, deleted flags, duplicate IDs, and per-task JSON before writing any row. A maximum of 1000 buffered pages, 10,000 active tasks and 16 MiB of serialized task snapshots bounds local staging; oversized or incomplete sets fail without changing the durable local cursor. Existing local mutations and an already-seeded outbox remain protected by the same transactional guards as the original bootstrap. The caller must use an **authenticated transport**, request each page with the exact previous `nextAfter` and unchanged checkpoint, and discard all collected pages on server HTTP 409. The parser does **not** itself fetch pages or prove a hostile/misrouted remote endpoint returned every task; it is not wired to native clients. Its synthetic tests include 103 records, delta replay, duplicate/reordered/mixed pages and pending-local-edit denial.

The new `GET /v1/bootstrap-page?limit=100` contract is **opt-in** and can enumerate more than 100 active tasks without a silent cutoff. It returns `schemaVersion`, `tasks`, numeric `checkpoint` (the ordered change-log sequence at first page), `nextAfter` (last returned UUID when additional records exist, otherwise `null`), `hasMore`, and `limit`. Pages are ordered by stable task UUID, not display priority.

For each subsequent page, request `GET /v1/bootstrap-page?limit=100&after=<nextAfter>&checkpoint=<checkpoint>` using the unchanged checkpoint and last `nextAfter`. Query parameters must not be duplicated; arbitrary/oversized cursors are rejected. When `hasMore=false`, the complete set is valid for the recorded checkpoint. Start subsequent delta reconciliation at `GET /v1/changes?after=<checkpoint>`, including changes committed after the final page. **If any committed task mutation occurs between page requests, the API responds 409 and the client must discard all previously collected pages and restart at the first page.** Do not merge conflicting pages or assume a partial set is complete.

Each request holds an independent SQLite read transaction for both the checkpoint and bounded keyset query. This is not a persistent multi-request server snapshot and does not freeze writers; under sustained concurrent writes a client may need to retry or wait for quiescence. It assumes all task writes pass through the existing transactional change-log API. No native client currently consumes this endpoint, and there is no multi-user auth, TLS, offline production sync, compaction or verified device acceptance. Existing `/v1/bootstrap` retains its 100-task safety limit for compatibility.

The bounded `GET /v1/tasks` preview returns `{"tasks":[...],"limit":N,"hasMore":boolean}`. It performs one ordered SQLite query with a one-row lookahead so callers can distinguish an incomplete view from a fully enumerated list. `hasMore: true` **does not** provide a continuation cursor or authorize treating the list as a full backup or synchronization snapshot. `GET /v1/bootstrap` is the atomic bounded initial-state contract and still rejects more than 100 active tasks instead of returning an incomplete state. Neither endpoint provides full-workspace pagination yet.

POST body example:

```json
{"title":"Plan a native release","priority":2,"due":"2026-11-07"}
```

Success returns `id`, `revision`, `title`, `priority`, `due`, `completed`, `createdAt`, `updatedAt`, and `deleted`. PATCH accepts a subset of those mutable fields. Task IDs are server-generated UUID strings. Revision conflicts return HTTP 409; unauthenticated access returns 401; invalid payloads return 4xx.

### Edit and delete retry receipts (development only)

PATCH and DELETE accept optional `Idempotency-Key` headers matching the 8–128
character safe-key syntax used for POST. Replaying exactly the same method,
task UUID, `If-Match` revision, and normalized body with the same key returns
the committed response **without** another revision or change event, including
a replay after a process restart or after a task was tombstoned. Reusing a key
for different content, a revision, another task, or a different method yields
HTTP 409. Invalid key syntax yields HTTP 400. Keys share the POST namespace.

These opt-in retry receipts are stored in the local plaintext SQLite ledger in
the same transaction as their corresponding edits and change events. Existing
unkeyed clients retain historical revision-conflict semantics; offline clients
must always supply and persist a stable mutation key to retry safely. There is
no workspace identity, device authorization, expiry, or key lifecycle yet; a
future multi-user service must partition receipts by tenant and actor before
use. No native client uses this API or ledger today.

### Origin metadata and historical data preservation

New change-feed entries include `mutationId`, the request's idempotency key if
supplied, otherwise null. The server upgrades existing single-user development
SQLite databases by adding a nullable column without discarding prior change
history, task rows or idempotency receipts. Historical entries remain null;
no origin is inferred. The experimental outbox can recognize an accepted local
edit/delete by matching task ID, originating key, operation and revision, even
if it receives the change feed before a client acknowledgement. This is not a
substitute for authenticated tenant-scoped event provenance, session management,
crash-safe local task/outbox transactions or conflict UI in a future service.

### Consistent initial snapshot (development only)

`GET /v1/bootstrap` requires the same bearer authorization as other task
endpoints. It returns `{"schemaVersion":1,"tasks":[...],"cursor":N}` from
**one SQLite read transaction**, preventing updates from falling between a
task listing and independently retrieved change cursor. The prototype refuses
snapshots above 100 active tasks with HTTP 413; it never silently drops tasks.
Clients must not treat a 413 as an empty or partial workspace. The matching
experimental `OfflineOutbox.seed_bootstrap()` accepts this payload only once
on an empty outbox with no pending local edits, then resumes with
`/v1/changes?after=N`. These components are **not wired to any native
client, network sync, account, or production deployment**; a future
multi-workspace design requires a new authorization and cursor contract.

## Tests

```sh
python3 -m unittest discover -s server/tests -v
python3 -m py_compile server/api.py server/retry_receipts.py
```

Tests start an ephemeral loopback server with a synthetic token and a temporary database. They verify authorization denial, validation, idempotent concurrent creation, revision conflicts, immutable change history, persistence after reopening, and basic recovery from invalid input. Passing tests do not establish penetration testing or release acceptance.

## Local, non-overwriting SQLite snapshots (development)

The new `server/backup.py` CLI uses SQLite's online backup API to produce a
consistent point-in-time copy, including uncheckpointed WAL transactions, while
the server may be operating. It validates `PRAGMA integrity_check` and the
expected API tables before publishing an output. It uses private temporary
files and exclusive hard-link creation so existing backup or database files are
not overwritten. Restoration is only to a **new path**, never an existing
live database. Backup and restore refuse symbolic links anywhere in the destination parent path, and also reject existing destination symlinks, to prevent inadvertently writing through a linked directory. This is a static path check, not a production race-proof dirfd/openat security boundary. Both commands operate on local files; no HTTP endpoint exists.

```sh
python3 server/backup.py backup --source /path/to/dev-tasks.sqlite3 --destination /private/backup.sqlite3
python3 server/backup.py restore --source /private/backup.sqlite3 --destination /private/restored.sqlite3
python3 -m unittest discover -s server/tests -v
```

**Security limits:** Snapshots are plaintext SQLite files with mode 0600; they
are not encrypted, rotated, monitored or uploaded automatically. Never place
private backups in this public repository. Store them securely outside shared
folders, independently verify restores, and establish a real retention/recovery
policy before production use. Creating a snapshot is **not** itself proof of a
complete disaster-recovery process. See `test_backup.py` for synthetic
round-trip, history/idempotency, no-overwrite, and corrupt-source checks.

## Required next engineering gates

1. Versioned schema and database migrations (never destructive updates).
2. Authenticated multi-tenant identity, scoped workspace/project access controls and denial tests.
3. Session/credential rotation, rate limiting and abuse prevention.
4. TLS reverse-proxy and locked-down private network topology.
5. Offline native clients with transactional conflict reconciliation, verified backup/recovery and tombstones.
6. Operating-system-managed service packaging, observability and security review.
7. Per-device installation, runtime, accessibility, and end-to-end sync acceptance.

Do not point any real clients or production DNS at this prototype.
