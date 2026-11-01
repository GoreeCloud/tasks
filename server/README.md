# GoreeCloud Tasks — Experimental Loopback API

**Status:** Implemented source prototype with automated tests; not a deployed, production-grade, multi-user, TLS-protected, supported native service. This development API must **not** be exposed on an external network.

## Purpose

This independent service foundation creates a contract for future authenticated task synchronization and native client interoperability. The first release remains **single-user** and intentionally separate from browser, Linux and Android local stores. None of those clients connect to it yet.

## Security properties implemented in source

- Binds exclusively to `127.0.0.1`; port configurable (default 3037).
- Refuses startup without `GOREETASKS_API_TOKEN` of at least 32 non-whitespace characters; never commits or logs the secret.
- All task/change endpoints require `Authorization: Bearer …`. Only `/healthz` is unauthenticated.
- No CORS response headers; browser cross-origin access is not enabled.
- Input validation and 64 KiB JSON request bounds; no unreviewed shell commands or executable payloads.
- Parameterized SQLite queries, transactions and WAL, private-directory permissions where supported.
- Idempotency-Key for task creation; conflicts on reused keys with divergent payloads.
- Optimistic revision preconditions for task edits and deletion to prevent silent stale overwrites.
- Soft deletion with immutable, ordered change-log snapshots and cursor-based pagination (100 events per page).
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
| GET | `/v1/tasks?limit=100` | Read up to 100 non-deleted tasks |
| GET | `/v1/tasks/{id}` | Read a task |
| POST | `/v1/tasks` | Create a task; requires `Idempotency-Key` (8–128 safe characters) |
| PATCH | `/v1/tasks/{id}` | Update title, priority, due, completed; requires `If-Match` integer revision |
| DELETE | `/v1/tasks/{id}` | Tombstone task; requires `If-Match` revision |
| GET | `/v1/changes?after=0&limit=100` | Immutable ordered changes with cursor/hasMore |

POST body example:

```json
{"title":"Plan a native release","priority":2,"due":"2026-11-07"}
```

Success returns `id`, `revision`, `title`, `priority`, `due`, `completed`, `createdAt`, `updatedAt`, and `deleted`. PATCH accepts a subset of those mutable fields. Task IDs are server-generated UUID strings. Revision conflicts return HTTP 409; unauthenticated access returns 401; invalid payloads return 4xx.

## Tests

```sh
python3 -m unittest discover -s server/tests -v
python3 -m py_compile server/api.py
```

Tests start an ephemeral loopback server with a synthetic token and a temporary database. They verify authorization denial, validation, idempotent concurrent creation, revision conflicts, immutable change history, persistence after reopening, and basic recovery from invalid input. Passing tests do not establish penetration testing or release acceptance.

## Local, non-overwriting SQLite snapshots (development)

The new `server/backup.py` CLI uses SQLite's online backup API to produce a
consistent point-in-time copy, including uncheckpointed WAL transactions, while
the server may be operating. It validates `PRAGMA integrity_check` and the
expected API tables before publishing an output. It uses private temporary
files and exclusive hard-link creation so existing backup or database files are
not overwritten. Restoration is only to a **new path**, never an existing
live database. Both commands operate on local files; no HTTP endpoint exists.

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
