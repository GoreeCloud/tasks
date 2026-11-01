# GoreeCloud Tasks

**Organize Everything. Accomplish More.**

GoreeCloud Tasks is a privacy-minded, original task-management product for personal work, projects, and eventually shared workspaces. This repository is the first development foundation for three separate applications: a **native browser web interface**, a **native GTK4/libadwaita Linux desktop application**, and a **native Kotlin/Jetpack Compose Android application**.

> **Release status: early development / not Stable.** The clients currently keep **separate device-local data**. They do not share accounts, synchronize, collaborate, or use GoreeCloud AI yet. Do not use this initial source as your sole authoritative task registry or replace Todoist before controlled acceptance and migration.

## Implemented in source

| Capability | Web | Linux | Android |
| --- | --- | --- | --- |
| Create, complete, reopen, delete tasks | Yes | Yes | Yes |
| Device-local persistence | Browser localStorage | SQLite | SQLite |
| Four priorities | Yes | Yes | Yes |
| Views and task filters | Inbox, Today, Upcoming, Priority, All, Completed | Open, Today, Upcoming, Priority, Completed, Project | Open, Today, Upcoming, Priority, Completed, Project |
| Projects | Create and assign tasks | Create and assign tasks | Create and assign tasks |
| Due dates | Date entry and views | Date entry and filtered views | Native date picker and filtered views |
| Search / edit title | Yes | Search and store-level title edit | Pending |
| JSON export / restore | Validated local export and explicit replacement restore | Pending | Pending |
| Accessibility and GC UI alignment | Initial design only | Initial native design only | Initial native design only |
| Multi-device synchronization | Not implemented | Not implemented | Not implemented |

Each app is native to its target platform. They are not web wrappers. They use GC UI's design language as the design authority; consumer compliance and visual acceptance are **not** asserted.

## Run the web app

Requires Python 3 for the local file server, or any equivalent static server:

```sh
python3 -m http.server 4173 --directory web --bind 127.0.0.1
```

Open http://127.0.0.1:4173 in a modern browser. Data is saved in that browser's local storage. Use **Export data** to retain a separate copy. **Restore backup** validates the file against schema 1 and requires explicit confirmation before replacing all local data. This is early-development backup tooling, not yet a proven disaster-recovery solution. If stored data is unreadable, the web client disables edits and refuses to generate a misleading empty export. Another browser tab modifying data will disable editing until reload; IndexedDB-based transactional storage remains planned.

## Run the Linux app

Install Python 3 with PyGObject, GTK4 and libadwaita from the Linux distribution. On a Debian-family system the relevant packages typically include `python3-gi`, `gir1.2-gtk-4.0` and `gir1.2-adw-1`.

```sh
python3 linux/app.py
```

For user-local desktop integration without sudo, see [Linux install/uninstall](linux/README.md). The source installer preserves device data on uninstall and has an isolated installation smoke test.

The app stores its database under `$XDG_DATA_HOME/goreecloud-tasks/tasks.sqlite3` (otherwise `~/.local/share/goreecloud-tasks/tasks.sqlite3`). Do not treat this early client as fully backed up or synchronized.

## Build Android

Requirements: Android SDK Platform 35, JDK 17, and Gradle 8.10.2. The Gradle project lives under `android/`:

```sh
gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

The Android application has an original first-party GC UI Iris native adaptive app icon for Android API 26+. The package ID is `com.goreecloud.tasks`; the project uses Kotlin and Jetpack Compose. The Android app stores tasks in private app-local SQLite with non-destructive v1 → v2 schema migration for project and due-date fields. It does **not** request Internet permission or claim shared synchronization. The Android unit suite tests pure view/filtering rules; the native debug build compiles the actual UI.

An Android APK is **not considered delivered** by its appearance in local build output or GitHub Actions artifacts. Any actual APK delivered to the owner must be inspected, extracted as a standalone `.apk`, and uploaded to the existing Google Drive `GoreeCloud/Artifacts` folder, with provenance and readback, as required by GoreeCloud governance.

## Experimental local API

`server/api.py` is a **single-user, loopback-only, authenticated development API** with SQLite storage, idempotent creates, revision-checked updates, soft deletion, and ordered change snapshots. It is a separate test domain: the web, Linux and Android clients do **not** connect to or sync with it. See [API limitations and local usage](server/README.md). Do not publicly expose this prototype.

## Verification

```sh
node --check web/app.mjs
node --test web/*.test.mjs
python3 -m unittest discover -s linux/tests -v
python3 -m py_compile linux/app.py linux/store.py server/api.py
python3 -m unittest discover -s server/tests -v
sh linux/tests/test_install.sh
```

GitHub Actions builds the Android debug variant separately. A build result does not prove physical-device behavior or release readiness.

## Project structure

- `web/` — browser-native task workspace and pure data/query model.
- `linux/` — first-party GTK4/libadwaita desktop UI and SQLite store.
- `android/` — first-party Android Kotlin/Compose UI and SQLite store.
- `server/` — experimental loopback-only authenticated API and integration tests.
- `docs/ARCHITECTURE.md` — data, security, and synchronization decisions.
- `docs/PRODUCT_REQUIREMENTS.md` — owner feature catalog mapped to staged acceptance.
- `docs/ROADMAP.md` — staged path to the requested capability catalog.
- `.github/workflows/verify.yml` — model tests, Python checks, Android build.

## Design, governance, and ownership

The sole GoreeCloud design authority is [GoreeCloud UI (GC UI)](https://github.com/GoreeCloud/gc-ui). Source colors, spacing, and UI concepts are modeled after GC UI Iris tokens. This source is not a copy of the retired design system.

GoreeCloud Tasks is a separate product and is **not** part of the stable GC UI Foundations release. Android and Linux rely on third-party native platform SDKs and libraries under their upstream terms.

This repo must not receive user passwords, access tokens, private tasks, export dumps, signing keys, or production databases. See [architecture](docs/ARCHITECTURE.md) and [roadmap](docs/ROADMAP.md).

## License

First-party code in this repository is provided under Apache License 2.0 (see `LICENSE`). Third-party frameworks and libraries retain their own licenses.
