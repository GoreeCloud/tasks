# GoreeCloud Tasks

**Open-source, self-hosted, native task management — development preview (0.1)**

GoreeCloud Tasks is an original, privacy-focused alternative to parts of Todoist and TickTick. This repository contains a **FastAPI + SQLite server**, **React web app**, **native Qt Quick 6.12 Linux app**, **native Kotlin/Compose Android app**, reviewed GoreeCloud UI source, tests, build scripts, workflow files and documentation.

**Not yet:** full competitor feature parity, native or complete offline client editing, Identity integration, multiuser sync, production deployment, signed Android release, packaged Linux installer, native habit calendar heatmaps and advanced statistics, reminders and RFC 5545 recurrence. A basic month calendar is now implemented. Platform source code does not establish hardware acceptance.

## Implemented foundation

- Token-protected API with no-store private responses, redacted validation errors and bounded 1 MiB streamed write bodies, owner-only newly created SQLite files, SQLite schema v4, projects, CRUD, due dates, task version checks, cursor-based change feed, redacted deletion tombstones, retry idempotency and additive migration from v1/v2.
- Tags, daily/weekdays/weekly/biweekly/monthly/yearly date-only recurrence, server-side search and pagination, serialized HTTP 409 revision conflicts, optional idempotent PATCH retries, JSON/VTODO export and bounded formula-guarded private CSV task download, explicit checksum-protected generic/Todoist-subset CSV task import, and verified synthetic online-backup / non-overwriting restore-drill CLI.
- React opt-in encrypted offline vault with an opt-in public-only offline app shell, tokenless local unlock and ciphertext-only backup and same-origin validated recovery, atomic stale-tab write rejection, manual standalone task drafts/title edits, explicit server-vs-local conflict comparison/requeue, conflict-safe replay and on-demand cursor-based changefeed pulls; consistent bounded web workspace snapshot covering up to 5,000 tasks rather than silently truncating list pages; projects, Today/Upcoming/Completed lists, month calendar, **accessible P1–P4 priority board**, **subtasks/parent selection with a child-task panel**, **daily habit check-ins, native name/notes editing, paginated check-in history, and streaks** (web, Android, Linux), task editor, search, tags/projects at creation, foreground focus timer and private VTODO calendar export and explicit CSV download.
- Native Qt Quick Linux and Kotlin/Compose Android clients now refresh projects and tasks from one consistent, bounded 5,000-record API snapshot (no silent 1,000-task truncation); Linux projects/search/filter, parent selection and task editing/deletion/completion; Android projects, filters, parent selection, task editing/deletion, priority, recurrence and tags.
- In-repository GoreeCloud UI Material 3 Expressive plus Compose Multiplatform source adapters; design token CSS.

See [features and backlog](docs/FEATURE_AUDIT.md), [API](docs/API.md), [sync protocol](docs/SYNC_PROTOCOL.md), [encrypted web offline workflow](docs/OFFLINE_WEB.md), [opt-in static offline app shell](docs/OFFLINE_APP_SHELL.md), [daily habits](docs/HABITS.md), [backup and recovery](docs/BACKUP_RECOVERY.md), [calendar export](docs/ICAL_EXPORT.md), [date-only recurrence](docs/DATE_RECURRENCE.md), [CSV import and separate CSV export](docs/CSV_IMPORT.md), [source CLI reference](docs/CLI_REFERENCE.md), [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md) and [dependency review](docs/DEPENDENCIES.md).

## Start the local server

Python 3.11 or newer:

    export GOREECLOUD_TASKS_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    export GOREECLOUD_TASKS_DATABASE="$PWD/.local-data/tasks.sqlite3"
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -e './server[test]'
    uvicorn goreecloud_tasks.app:create_app --factory --host 127.0.0.1 --port 8000

Keep the token secret; a random 32+ character value is mandatory. The service binds to localhost. Never expose it to untrusted networks without HTTPS and additional security controls.

## React web app

Node.js 22+:

    cd web
    npm ci
    npm run dev

Open http://127.0.0.1:5173 and paste the secret token. Vite proxies /api to localhost:8000. The token is held in tab memory and cleared on disconnect/reload. Build static assets with npm run build. Production hosting needs HTTPS reverse proxy routing /api to the server.

## Native Linux

Python 3.11+, PySide6 6.12.0 and graphical Qt environment:

    python3 -m venv .linux-venv
    . .linux-venv/bin/activate
    pip install -r linux/requirements.txt
    export GOREECLOUD_TASKS_URL=http://127.0.0.1:8000
    export GOREECLOUD_TASKS_API_TOKEN='<same private API secret>'
    python linux/main.py

Off-machine API hosts require HTTPS. This is a native Qt Quick graphical app, not an Electron/Tauri shell; release packaging and real display-session tests are not complete.

## Native Android

JDK 17+, SDK platform 37.1 and repository Gradle wrapper:

    cd android
    ./gradlew :app:assembleDebug

Compose uses the approved GoreeCloud Material 3 Expressive theme as its outer host and shared Compose Multiplatform UI source from vendor/gc-ui, resolved through local composite builds (no fictitious Maven artifact). The app asks for HTTPS server URL and API token; only Android debug emulator may use http://10.0.2.2:8000. No signed release or physical-device acceptance yet.

## Tests

    python -m pytest server/tests -q
    cd web && npm ci && npm run build && npm test

See GitHub workflow checks for build evidence at specific commits. No deployment is performed by this repository. The [real-browser UI acceptance evidence](docs/REAL_BROWSER_UI_ACCEPTANCE_20261120.md) documents reproducible Chromium/Firefox/WebKit synthetic task workflows and the narrow mobile reflow fix. The optional `cd web && npm run browser:acceptance` test requires explicitly supplied, inspected local browser binaries and never logs into a real service.

## Privacy, security and licenses

No product telemetry or SaaS account is implemented. SQLite data remains operator-owned; web and Android credentials stay in memory. Shared bearer token is single-user development authentication, **not** GoreeCloud Identity or device-level access control. Protect database backups and use a trusted TLS gateway for remote access.

GoreeCloud UI is the design pillar; GoreeCloud Mesh is integration; GoreeCloud Identity governs access; GoreeShield governs privacy; Wardveil governs cybersecurity. Only source-level UI integration exists. Other MIPS runtime controls are pending and are not implied.

Original Tasks source is **MIT licensed**, see [LICENSE](LICENSE). MIT GoreeCloud UI snapshots retain their original upstream license and pinned provenance at [vendor/gc-ui/PROVENANCE.md](vendor/gc-ui/PROVENANCE.md). Other dependencies have their own licenses; Qt/PySide6 LGPL compliance must be reviewed before binary distribution. No proprietary or AGPL competitor source was copied.

**Maturity: early development only.**
