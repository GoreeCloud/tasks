# GoreeCloud Tasks

**Open-source, self-hosted, native task management — development preview (0.1)**

GoreeCloud Tasks is an original, privacy-focused alternative to parts of Todoist and TickTick. This repository contains a **FastAPI + SQLite server**, **React web app**, **native Qt Quick 6.12 Linux app**, **native Kotlin/Compose Android app**, reviewed GoreeCloud UI source, tests, build scripts, workflow files and documentation.

**Not yet:** full competitor feature parity, client offline edits, Identity integration, secure multiuser sync, a production service, signed Android release, packaged Linux installer, habits, notifications or calendar grid. Platform source code does not establish hardware acceptance.

## Implemented foundation

- Token-protected versioned API and SQLite database, projects, task CRUD, description, priorities and date-only due dates.
- Tags, simple daily/weekly/monthly recurrence, server-side status/due/search filters, HTTP 409 revision conflicts, JSON export.
- React list, projects, Today/Upcoming/Completed, task editor, search, foreground focus timer.
- Native Qt Quick Linux list/create/complete and Android Jetpack Compose list/create/complete.
- In-repository GoreeCloud UI Material 3 Expressive plus Compose Multiplatform source adapters; design token CSS.

See [features and backlog](docs/FEATURE_AUDIT.md), [API](docs/API.md), [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md) and [dependency review](docs/DEPENDENCIES.md).

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
    cd web && npm ci && npm run build

See GitHub workflow checks for build evidence at specific commits. No deployment is performed by this repository. The [real-browser UI acceptance evidence](docs/REAL_BROWSER_UI_ACCEPTANCE_20261120.md) documents reproducible Chromium/Firefox/WebKit synthetic task workflows and the narrow mobile reflow fix. The optional `cd web && npm run browser:acceptance` test requires explicitly supplied, inspected local browser binaries and never logs into a real service.

## Privacy, security and licenses

No product telemetry or SaaS account is implemented. SQLite data remains operator-owned; web and Android credentials stay in memory. Shared bearer token is single-user development authentication, **not** GoreeCloud Identity or device-level access control. Protect database backups and use a trusted TLS gateway for remote access.

GoreeCloud UI is the design pillar; GoreeCloud Mesh is integration; GoreeCloud Identity governs access; GoreeShield governs privacy; Wardveil governs cybersecurity. Only source-level UI integration exists. Other MIPS runtime controls are pending and are not implied.

Original Tasks source is **MIT licensed**, see [LICENSE](LICENSE). MIT GoreeCloud UI snapshots retain their original upstream license and pinned provenance at [vendor/gc-ui/PROVENANCE.md](vendor/gc-ui/PROVENANCE.md). Other dependencies have their own licenses; Qt/PySide6 LGPL compliance must be reviewed before binary distribution. No proprietary or AGPL competitor source was copied.

**Maturity: early development only.**
