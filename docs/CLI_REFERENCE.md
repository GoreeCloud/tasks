# GoreeCloud Tasks — CLI source reference

**Owner:** GoreeCloud/tasks. **Date:** 2026-11-21 America/Chicago.
**Status:** development-stage source commands. **Intended canonical Drive registry:** GoreeCloud/CLI Commands/GoreeCloud/Tasks.md. That Drive record must be synchronized and verified independently; this repo document is not proof of such a write.

All examples use explicit placeholders, not real tokens, hostnames, personal data or authorized production endpoints. Do not use on a live Vikunja instance or personal task database.

| Command | Purpose | Risk | Verified boundary |
| --- | --- | --- | --- |
| python -m pytest server/tests -q | Run deterministic API/security tests | Read-only test database | 61 API tests passed locally, including streamed-body cap, privacy and date-only recurrence |
| npm ci && npm run build | Install pinned web dependencies and build | Changes developer workspace | Local web production build passed |
| npm test | Check source/browser contract tests | Read-only | 5 local tests passed, including fail-closed offline shell cache generation |
| npm run preview -- --port 18758 --strictPort | Serve built public web assets and offline-sw.js on localhost for isolated test only | Local network listener | Passed on 127.0.0.1 in synthetic Chromium acceptance; never expose test server publicly |
| GC_PLAYWRIGHT_CORE_MODULE=... GC_CHROMIUM_BIN=... node tests/offline-shell-acceptance.mjs | Real Chromium browser test using explicit inspected local binaries, localhost fixture and synthetic API | Starts and destroys isolated browser | Passed opt-in worker, CacheStorage public-only, offline reload and tokenless vault; requires explicit preinstalled binary paths |
| python linux/smoke.py | Offscreen Qt Quick launch smoke | UI-only | Passed with QT_QPA_PLATFORM=offscreen |
| python -m unittest discover -s linux/tests -v | Native Linux filter/model tests | Read-only | 6 passed locally, including full-snapshot validation and refresh request |
| ./gradlew :app:assembleDebug | Build Android debug APK | Changes local build directory | Local Gradle build succeeded; no device acceptance |
| python -m goreecloud_tasks.backup verify --database FILE | Verify SQLite integrity and FKs | Read-only, may hold read lock | Verified against ephemeral test database |
| python -m goreecloud_tasks.backup backup --database FILE --output NEWFILE | Online backup to new private file | Writes backup; no overwrite | Verified against ephemeral test database |
| python -m goreecloud_tasks.backup restore-drill --backup FILE --output NEWFILE | Reconstruct schema-v4 backup into a new, owner-only SQLite file; verify tables, counts, feed cursor and integrity | Changes disposable output file; refuses overwrites | Tested against synthetic tasks and habits, no production restore |
| uvicorn goreecloud_tasks.app:create_app --factory --host 127.0.0.1 --port 8000 | Serve local API | Network-facing on loopback | Source contract, not production acceptance |

## Development invocation examples

Run from repository root, only on an authorized development computer:

    python3 -m venv .venv
    . .venv/bin/activate
    pip install -e './server[test]'
    python -m pytest server/tests -q

    export GOREECLOUD_TASKS_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    export GOREECLOUD_TASKS_DATABASE="./data/tasks.sqlite3"
    uvicorn goreecloud_tasks.app:create_app --factory --host 127.0.0.1 --port 8000

    cd web
    npm ci
    npm run build
    npm test
    # Optional offline browser acceptance: separately serve built dist on localhost
    npm run preview -- --port 18758 --strictPort
    # In another terminal after verifying existing browser binaries:
    GC_PLAYWRIGHT_CORE_MODULE=/path/to/playwright-core/index.mjs GC_CHROMIUM_BIN=/path/to/verified/chrome node tests/offline-shell-acceptance.mjs

    cd android
    ./gradlew :app:assembleDebug --no-daemon --console=plain

    QT_QPA_PLATFORM=offscreen python linux/smoke.py
    QT_QPA_PLATFORM=offscreen python -m unittest discover -s linux/tests -v

    python -m goreecloud_tasks.backup verify --database /path/to/owned/tasks.sqlite3
    python -m goreecloud_tasks.backup backup --database /path/to/owned/tasks.sqlite3 --output /path/to/private/new-snapshot.sqlite3
    python -m goreecloud_tasks.backup restore-drill --backup /path/to/private/new-snapshot.sqlite3 --output /path/to/private/disposable-restored.sqlite3

**Authentication:** API requires environment variable GOREECLOUD_TASKS_API_TOKEN with a newly generated random secret of length 32+; never store its value in the repository, in Drive CLI docs, or in logs. The Linux client additionally accepts GOREECLOUD_TASKS_URL; only loopback HTTP or HTTPS is allowed. Android app uses an in-memory token (no CLI login).

**Failure / rollback:** Inspect sanitized local stdout/CI logs. On failure to build, remove disposable build outputs only after ensuring they are not user-owned. Do not delete SQLite files or -wal files to clear an error. Existing backups are never overwritten by the backup CLI. If migration to schema v4 is unsupported by a previous binary, restore a consistent pre-migration backup on an isolated test instance before any authorized production rollback. Do not downgrade live database files.

**Unverified:** VPS deployment, user task restore, remote TLS/Identity access, native installation on physical devices, signed release packages. All canonical runtime state must be verified in owning systems before operational claims.
