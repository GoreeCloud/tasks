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
| Views and task filters | Inbox, Today, Next 7 days, Overdue, Upcoming, Priority, All, Completed | Open, Today, Next 7 days, Overdue, Upcoming, Priority, Completed, Project | Open, Today, Next 7 days, Overdue, Upcoming, Priority, Completed, Project |
| Projects | Create and assign tasks | Create and assign tasks | Create and assign tasks |
| Priority filter / sorting | All/P1–P4; Smart/Due date/Newest/Title | All/P1–P4; Smart/Due date/Title | All/P1–P4; Smart/Due date/Title |
| GC UI appearance | Light default, Neutral + 5 accents, local preference | Light default, Neutral + 5 accents, private XDG preference | Light default, Neutral + 5 accents, private preferences |
| List-first navigation | Desktop project rail + mobile Today/Inbox/Add/Search/Browse | GTK sidebar, compact capture | Compose native bottom tabs, Browse + FAB composer |
| Bulk actions | Visible-task selection, complete/reopen, priority, project moves, local Trash | Native visible-task multi-select; complete/reopen/priority/project/Trash | Native visible-task multi-select; complete/reopen/priority/project/Trash |
| Keyboard workflow | / search, N quick add, skip-to-content link | Ctrl+N task capture, Ctrl+F search | Hardware-keyboard acceptance pending |
| Due dates | Date entry and views | Date entry and filtered views | Native date picker and filtered views |
| Search / task editing | Search and dialog for title, priority, due date and project | Native search and task edit dialog | Native search and task editing (device acceptance pending) |
| JSON export / restore | Validated local export and explicit replacement restore | Compatible CLI + GTK file dialogs, empty-store import (no overwrite) | Native document-picker export, guarded empty-store import |
| Accessibility and GC UI alignment | Initial design only | Initial native design only | Initial native design only |
| Multi-device synchronization | Not implemented | Not implemented | Not implemented |

The owner-reference-inspired native navigation pass is documented in [native list-first UI](docs/NATIVE_LIST_FIRST_UI.md). The Android implementation requires the latest CI build and new physical-device visual/accessibility acceptance; the GTK native source/smoke test is not full visual acceptance.

Each app is native to its target platform. They are not web wrappers. They use GC UI's design language as the design authority; consumer compliance and visual acceptance are **not** asserted. The appearance settings now offer explicit Light/Dark modes and Neutral, Lagoon, Moss, Ember, Ocean and Iris accents, with first-run **Light/Neutral**. Preferences are retained separately on each device; no theme setting is synchronized or included in task backups. See [GC UI appearance integration](docs/GC_UI_APPEARANCE_MIGRATION.md).

## Run the web app

Requires Python 3 for the local file server, or any equivalent static server:

```sh
python3 -m http.server 4173 --directory web --bind 127.0.0.1
```

Open http://127.0.0.1:4173 in a modern browser. Data is saved in that browser's local storage. The **Edit** action opens an accessible browser dialog for a task's title, P1–P4 priority, due date and project; changes preserve identity and completion history and pass through the existing stale-tab write check. Deletions now move tasks into **durable browser-local Trash**, visible in the navigation, with Restore actions and a shortcut to restore the latest deletion. A validated local storage envelope keeps active tasks and up to 1,000 deleted task records in a single localStorage write (3 MiB total limit), preserving task identities, project references and historical timestamps across page reloads. Existing schema-1 browser data remains readable and migrates only on a successful edit. The local Trash is **not included in portable JSON exports**, and it is not synchronized or a replacement for an independent backup. A colliding task ID blocks importing a backup without overwriting current data or Trash. See [browser Trash recovery and limitations](docs/BROWSER_TRASH_RECOVERY.md). Use **Export data** to retain a separate copy. **Restore backup** validates the file against schema 1 and requires explicit confirmation before replacing active tasks and projects, while retaining recoverable local Trash. This is early-development backup tooling, not yet a proven disaster-recovery solution. If stored data is unreadable, the web client disables edits and refuses to generate a misleading empty export. Another browser tab modifying data will disable editing and refuse a misleading stale backup export until reload. Keeping active tasks and Trash in one key prevents half-saved deletes, but does **not** prevent simultaneous independent writes from two tabs. IndexedDB-based transactional storage remains planned.

The browser dashboard now includes a **completion-rate metric**, **Overdue** and **Next 7 days** views, priority filters, sorting and bulk task operations on selected visible tasks. Bulk edits use the existing browser-local stale-tab guard and preserve the schema-1 portable JSON contract. Use **/** to focus search or **N** to focus Quick Add when no other control is active. The design follows GC UI semantic roles and responsive layouts. Automated real-browser Chromium/Firefox task workflows, schema-1 export/import into a clean profile, mobile reflow, effective 200% CSS zoom and axe checks are now covered with synthetic data; human screen-reader, actual browser zoom and visual acceptance remain pending. See [browser runtime acceptance](docs/BROWSER_RUNTIME_ACCEPTANCE.md). See [the browser productivity upgrade](docs/WEB_PRODUCTIVITY_UPGRADE.md) for safety boundaries and test coverage.

## Run the Linux app

Install Python 3 with PyGObject, GTK4 and libadwaita from the Linux distribution. On a Debian-family system the relevant packages typically include `python3-gi`, `gir1.2-gtk-4.0` and `gir1.2-adw-1`.

```sh
python3 linux/app.py
```

Linux now supports native Overdue and Next 7 days views, priority and sorting filters, plus atomic multi-select bulk completion, reopening, reprioritization, project moves and recoverable Trash transfers. The native SQLite schema remains unchanged. See [native view parity and remaining acceptance](docs/NATIVE_VIEW_PARITY.md).

For user-local desktop integration without sudo, see [Linux install/uninstall](linux/README.md). The source installer preserves device data on uninstall and has an isolated installation smoke test.

The app stores its database under `$XDG_DATA_HOME/goreecloud-tasks/tasks.sqlite3` (otherwise `~/.local/share/goreecloud-tasks/tasks.sqlite3`). Do not treat this early client as fully backed up or synchronized. Linux deletions now move tasks into durable, local-only SQLite Trash; the native Trash view can restore them across app restarts. **Portable JSON backups do not include Trash records**. See [Linux recovery details](linux/README.md).

## Build Android

Requirements: Android SDK Platform 35, JDK 17, and Gradle 8.10.2. The Gradle project lives under `android/`:

```sh
gradle -p android :app:testDebugUnitTest :app:assembleDebug
```

The Android application has an original first-party GC UI Iris native adaptive app icon for Android API 26+. The package ID is `com.goreecloud.tasks`; the project uses Kotlin and Jetpack Compose. The Android app stores tasks in private app-local SQLite with non-destructive v1 → v5 migrations for projects, due dates, completion timestamps, exact imported portable timestamps, and private recoverable Trash. It does **not** request Internet permission or claim shared synchronization. The Android unit suite tests pure view/filtering rules; the native debug build compiles the actual UI.

Android includes a native **Export private JSON backup** action using the
system document picker and the browser/Linux portable schema-1 format
(2 MiB maximum; 10,000 tasks and 10,000 projects). Export does not request
Internet or storage permissions. Completed records created before v3 can lack
accurate completion timestamps; rather than invent dates, the app refuses
lossy export until those tasks are reopened and completed again. Android import preserves Linux microsecond timestamps without rounding away source precision. It validates schema-1 JSON using a size-bounded document picker,
requires a second confirmation, and restores only into an empty database
using an all-or-nothing SQLite transaction. Import is blocked whenever local Trash contains deleted tasks, even if active tasks/projects are empty. Android deletion now moves full task rows into durable private SQLite Trash, with a native Trash view to restore them across app restarts. Portable JSON exports deliberately exclude Trash history; preserving it requires a verified database backup. Restoration refuses ID conflicts and missing original projects without overwriting data. The new v5 migration and recovery behavior are covered by Robolectric tests; physical-device Trash acceptance remains pending. SQLite transaction recovery is now covered by Robolectric JVM tests on a
synthetic Android context: round trips, protected existing rows, upgrade and
mid-transaction rollback. A guarded physical-device smoke on a OnePlus (Android 16) verified native launch, schema-1 document-picker export, populated-workspace import blocking and one synthetic task restore. Full device, accessibility, other-provider and release acceptance remain pending; see [Android physical-device test evidence](docs/ANDROID_DEVICE_ACCEPTANCE.md). These JSON
files are unencrypted: store them privately and verify restoration elsewhere.

A shared [portable backup compatibility fixture](fixtures/portable/README.md) is validated and round-tripped by the web, Linux and Android test suites so changes to Unicode, project links, timestamp precision or completed-task metadata cannot silently drift between clients. A shared strict timestamp contract additionally rejects impossible dates/hours, missing seconds, unsupported offsets and ambiguous time-zone-free values across platforms instead of silently normalizing them. Android export normalizes legacy timestamp strings that an older Android parser accepted without seconds while preserving the stored instant; exact portable timestamps retain their original precision and timezone offset. Existing malformed browser-local data is treated as unreadable rather than silently repaired.

The CI build checks the compiled APK identity, SDK bounds, signature, Android automatic-backup policy, forbidden network/storage permissions and SHA-256 using `android/tests/verify_debug_apk.sh`, then temporarily stores the
compiled APK as a GitHub Actions artifact for internal testing. GitHub wraps
this file in a ZIP; this is not a public APK release, signed production build,
or end-user delivery. Artifact retention is seven days.

An Android APK is **not considered delivered** by its appearance in local build output or GitHub Actions artifacts. Any actual APK delivered to the owner must be inspected, extracted as a standalone `.apk`, and uploaded to the existing Google Drive `GoreeCloud/Artifacts` folder, with provenance and readback, as required by GoreeCloud governance.

The Android Compose client exposes Overdue, Next 7 days, priority filters, sorting, and selected-visible-task bulk completion/reopening, reprioritization, project/Inbox moves and confirmed recoverable Trash. These changes preserve the existing SQLite schema and portable JSON. The date-view/filter upgrade passed Android CI; the new native bulk operations require their own CI and physical-device acceptance. See [native views](docs/NATIVE_VIEW_PARITY.md) and [native bulk operations](docs/NATIVE_BULK_OPERATIONS.md).

## Experimental local API

`server/api.py` is a **single-user, loopback-only, authenticated development API** with SQLite storage, idempotent creates, optional durable edit/delete retry receipts, revision-checked updates, soft deletion, and ordered change snapshots. It is a separate test domain: the web, Linux and Android clients do **not** connect to or sync with it. See [API limitations and local usage](server/README.md). Do not publicly expose this prototype.

## Experimental offline outbox

`server/outbox.py` is an isolated, durable SQLite mutation queue and remote
projection for **future** offline synchronization. It retains idempotency keys,
tracks conflicts, recognizes matching mutation origins, and atomically applies checked single-user API change pages
with their cursor. It has no network transport, account identity, tokens, or
native client integration. A versioned, authenticated, one-transaction bootstrap prototype is also available for up to 100 active tasks. It **does not synchronize tasks yet**. See
[offline outbox status and limitations](docs/OFFLINE_OUTBOX_PROTOTYPE.md).

## Verification

```sh
node --check web/app.mjs
node --test web/*.test.mjs
python3 -m unittest discover -s linux/tests -v
python3 -m py_compile linux/app.py linux/store.py linux/backup.py server/api.py
python3 -m unittest discover -s server/tests -v
python3 -m py_compile server/backup.py server/outbox.py server/retry_receipts.py
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
- `docs/WEB_PRODUCTIVITY_UPGRADE.md` — browser-only productivity controls and acceptance gaps.
- `docs/NATIVE_VIEW_PARITY.md` — native due-date views and priority/sort UI with verification boundaries.
- `docs/NATIVE_BULK_OPERATIONS.md` — native transactional multi-selection and recoverable batch actions.
- `docs/GC_UI_APPEARANCE_MIGRATION.md` — app-local Light-first GC UI semantic theme integration and acceptance gaps.
- `docs/BROWSER_RUNTIME_ACCEPTANCE.md` — real Chromium/Firefox synthetic E2E, screenshot/zoom and accessibility checks.
- `docs/UI_INSPIRATION_DIRECTION.md` — owner-supplied visual references, GC UI adaptation, browser list-first implementation and native follow-ups.
- `.github/workflows/verify.yml` — model tests, Python checks, Android build.

## Design, governance, and ownership

The sole GoreeCloud design authority is [GoreeCloud UI (GC UI)](https://github.com/GoreeCloud/gc-ui). Source colors, spacing, and UI concepts are modeled after GC UI Iris tokens. This source is not a copy of the retired design system.

GoreeCloud Tasks is a separate product and is **not** part of the stable GC UI Foundations release. Android and Linux rely on third-party native platform SDKs and libraries under their upstream terms.

This repo must not receive user passwords, access tokens, private tasks, export dumps, signing keys, or production databases. See [architecture](docs/ARCHITECTURE.md) and [roadmap](docs/ROADMAP.md).

## License

First-party code in this repository is provided under Apache License 2.0 (see `LICENSE`). Third-party frameworks and libraries retain their own licenses.

Portable schema 2 supports optional plain-text task descriptions across the browser, Linux and Android. Existing schema-1 backups remain readable; notes require schema-2-aware readers. See [compatibility and recovery gates](docs/PORTABLE_SCHEMA2_DESCRIPTIONS.md).
