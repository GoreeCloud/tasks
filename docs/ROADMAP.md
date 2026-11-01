# GoreeCloud Tasks — Feature and Release Roadmap

**Stage:** Early development. The user's complete 16-category product specification is the product destination, not an inventory of implemented features.

## A. Foundation (in progress)

- [x] Public `GoreeCloud/tasks` repository initialized with first-party web, Linux, Android sources.
- [x] Device-local task creation, completion, reopening, deletion, and P1–P4 priorities in all three clients (source implemented; verification tracked separately).
- [x] Web inbox/project creation, date entry, search, completed history, themes, validated JSON export/restore and stale-tab write protection (source; comprehensive recovery validation pending).
- [x] Web native HTML edit dialog for title, priority, due date and project using shared create/edit validation, preserved completion metadata and stale-tab write gate; pure field and backup round-trip tests (browser visual acceptance pending).
- [x] Web productivity dashboard: Overdue and Next 7 days views, priority filtering, sorting, bulk complete/reopen/priority/project/Trash operations, completion-rate metric, keyboard shortcuts and responsive GC UI controls; browser model and static UI tests added. Schema 1 retained; human browser/AT acceptance pending.
- [x] Web durable local Trash with native browser Restore view and latest-deletion shortcut: backward-compatible legacy schema-1 read, atomic same-key active/Trash updates, strict persisted record validation and 1,000-record/3 MiB limits, exact completion history, orphan-reference/ID-collision protections, and restart/regression tests. Portable JSON exports exclude Trash. True concurrent-tab transactional writes remain pending.
- [x] Linux GTK and Android Compose projects (source).
- [x] Linux project creation/assignment, task view filters, due date capture and local search (source; GUI and device validation pending).
- [x] Native Linux task edit dialog for title, priority, due date and project with atomic store update and negative validation tests; GUI acceptance pending.
- [x] Linux durable SQLite Trash and GTK Restore view: additive non-destructive schema, atomic delete/recovery, exact task history retention, restart and conflict rollback tests, native GTK recovery smoke, and guarded backup import when local Trash is nonempty. Local Trash is explicitly excluded from portable JSON; cross-device Trash recovery and formal GUI acceptance pending.
- [x] Linux user-local desktop integration scripts and icon, with isolated install/uninstall test preserving local task data; distro acceptance pending.
- [x] Browser-compatible schema-1 Linux JSON export and guarded empty-store import via CLI and native GTK file dialogs, with round-trip tests; full native recovery acceptance pending.
- [x] Android native project creation/assignment, due-date picker, Today/Upcoming/Project filters and non-destructive schema v2 migration (source; device verification pending).
- [x] Android non-destructive schema-v4 completion metadata and exact Linux-compatible timestamp preservation, native JSON export and guarded schema-1 empty-store import with confirmation and atomic rollback; broader real-device recovery validation pending.
- [x] Android v5 additive device-local SQLite Trash with native Compose Restore view: atomic delete/restoration, exact portable timestamp preservation, fail-closed missing-project and duplicate-ID handling, and import blocked when Trash is populated. Robolectric migration and transaction tests added; full real-device acceptance still pending. Trash is excluded from portable JSON.
- [x] CI verifies native Android debug APK signature, package/SDK identity, no network or broad storage access, disabled automatic backup, and SHA-256; retains only a short-lived internal build artifact. Governed standalone Drive APK delivery and full device sign-off remain pending.
- [x] Limited Android 16 physical-device acceptance: native launch, Android picker JSON export, guarded import rejection, and a synthetic one-task save/restore passed; temporary test app and files removed. See [evidence](ANDROID_DEVICE_ACCEPTANCE.md); full device sign-off and standalone Drive APK handoff pending.
- [x] Shared synthetic portable schema-1 fixture used by browser, Linux SQLite and Android/Robolectric restore tests to catch Unicode/project/date/microsecond contract drift (no production data).
- [x] Shared strict timestamp acceptance/rejection matrix enforced by web, Linux and Android backup parsers; avoids JavaScript normalization of invalid calendar dates, Linux accepting nonportable offsets, and Android accepting missing seconds. Android exporter normalizes legacy nonportable timestamps to recoverable ISO values without changing their stored instant. Full device/provider recovery acceptance still pending.
- [x] Android Robolectric SQLiteOpenHelper recovery regression tests: complete synthetic export/import round trip, non-overwrite for existing data, rollback on mid-import failure, completion metadata, and v3-to-v4 preservation (other provider/device combinations pending).
- [x] Android task-editing dialog for title, priority, due date and project with pure validation unit tests (source; device verification pending).
- [x] Hardened text/priority validation and portable backup boundary cases across native clients; Android verification relies on CI/device tests.
- [ ] Verify all platform builds and runtime operation, fix defects, audit accessibility and GC UI appearance.
- [ ] Desktop packaging, Android device validation, and standalone APK handoff if requested.

- [x] Additional native Linux and Android UI source for Overdue/Next 7 days views, P1–P4 priority filtering, and Smart/Due date/Title sorting. Existing native data schema and backups unchanged. Linux unit and GTK runtime smoke covered and previous Android CI succeeded; real-device UI acceptance remains pending. See [native view parity](NATIVE_VIEW_PARITY.md).
- [x] Native Linux and Android batch-edit source: select visible tasks and apply complete/reopen, P1–P4, project/Inbox move or confirmed recoverable Trash in a single validated SQLite transaction; rejects stale/duplicate IDs and rolls back on Trash collisions. Linux unit and GTK smoke validation added; Android Robolectric/CI must pass at this commit, device accessibility pending. See [native bulk operations](NATIVE_BULK_OPERATIONS.md).

- [x] GC UI appearance integration: browser semantic snapshot pinned to GC UI, Light/Neutral first launch, explicit Light/Dark and accent choices stored separately from tasks across browser, Linux GTK4 and Android Compose. Browser/Linux unit and GTK smoke checks added; Android CI and real UI/device accessibility acceptance are separate gates. See [GC UI appearance migration](GC_UI_APPEARANCE_MIGRATION.md).

- [x] Browser real-runtime acceptance runner using pinned test-only Playwright and axe-core: Chromium and Firefox synthetic task create/edit/bulk/Trash/backup restore; mobile and effective 200% CSS zoom reflow, semantic feedback and accessible checkbox labels; screenshot evidence produced by QA, with automatic CI execution. Real browser toolbar zoom, human screen-reader, full contrast/RTL/device matrices and full Stable release acceptance remain open. See [browser runtime acceptance](BROWSER_RUNTIME_ACCEPTANCE.md).

- [x] Owner-reference-inspired browser list-first visual pass: compact desktop Inbox/Today/Projects hierarchy, clean task rows and due/priority metadata, accessible mobile bottom tabs, Browse dialog and floating Add composer, with GC UI semantic palettes rather than copied third-party branding. Chromium/Firefox runtime and effective-zoom checks required; real mobile/GTK native acceptance remains open. See [UI inspiration direction](UI_INSPIRATION_DIRECTION.md).

- [x] Native list-first navigation source for Android Compose (Today/Inbox/Search/Browse bottom dock, FAB capture, settings and context row actions) and Linux GTK4 (native view rail, compact header and collapsible form); storage and portable JSON schema unchanged. Local GTK smoke and Android JVM UI-route tests added. Android CI and physical-device/Orca/large-text acceptance are separate gates. See [native list-first UI](NATIVE_LIST_FIRST_UI.md).

- [x] GTK4 screenshot-led layout correction: view/project Browse popover under 700px, live project counts, hidden idle batch controls, collapsible advanced filters/new-project form, Ctrl+N/Ctrl+F, true mapped 600×480 and 940×760 synthetic CI smoke. Assistant-reviewed Light/Dark screenshots; owner/Orca/large-text and Android physical acceptance remain open. See [native list-first UI](NATIVE_LIST_FIRST_UI.md).

## B. Personal productivity

- [ ] Shared versioned task domain model, nesting, labels, descriptions, attachments, priorities, bulk edits and templates.
- [ ] Consistent Inbox/Today/Upcoming/Project/Completed across all native clients.
- [ ] Date/time/time zone, recurrence, reminders and native notifications.
- [ ] Accessible list/board/calendar layouts, keyboard and screen-reader acceptance.
- [ ] Search, saved filters, CSV and validated import/export with restore drills.
- [ ] Reliable offline operation across process restarts and failure modes.

## C. Self-hosted sync, identity and teams

- [x] Experimental single-user loopback-only API with authenticated request gate, idempotent creates, revision-checked updates, soft-deletion change feed and integration tests (not connected to clients; not production deployable).
- [x] Experimental offline SQLite backup CLI with integrity-checked, non-overwriting point-in-time snapshots and restoration only to a new database (plaintext development tooling; full recovery procedures pending).
- [x] Durable, offline SQLite outbox *reference* with mutation retries, a remote projection, guarded conflict preservation, atomic cursor updates and single-user API contract tests; not wired to native clients or a network.
- [x] Experimental authenticated single-user bootstrap endpoint with consistent snapshot/cursor and fail-closed 100-task cap, plus guarded outbox initialization and regression tests; not deployed or connected.
- [x] Experimental optional PATCH/DELETE idempotency receipts with atomic success replay, concurrent retry and rollback tests; native client integration and multi-tenant isolation pending.
- [x] Non-destructive experimental mutation-origin event metadata and outbox acknowledgement-before/after-pull contract tests; still no native client transport or workspace authorization.
- [x] Fail-closed queued-mutation payload verification before origin acknowledgement, with page-level rollback and strict type comparison tests.

- [ ] Secure API and PostgreSQL migrations with per-tenant access controls.
- [ ] Authentication, device sessions, invitation and role policies.
- [ ] Authenticated delta synchronization, conflict reconciliation and tombstones.
- [ ] Shared projects, assignments, comments, activity log, collaboration updates.
- [ ] Backups, disaster-recovery tests and operational runbooks.

## D. Automation, analytics and AI

- [ ] Native notifications and calendar integrations with granular provider consent.
- [ ] Workflow engine with idempotency, event tracing, retries and monitoring.
- [ ] Personal/project/team analytics and productivity goal settings.
- [ ] Opt-in GoreeCloud AI task decomposition, natural-language capture, text/document/email extraction.
- [ ] Secure connectors (Gmail, Google Calendar, Microsoft providers, Slack, Notion, Jira, time trackers, automation providers) gated by individual grants.
- [ ] Audited developer API, webhooks, SDK, CLI and MCP compatibility.

## E. Platform maturity and expansion

- [ ] Stable acceptance backed by platform-specific security, build, installation, runtime, accessibility, recovery, upgrade and rollback evidence.
- [ ] Reconciled Todoist migration only after controlled Stable acceptance; do not retire the interim registry early.
- [ ] Decide Windows, macOS, iOS and wearable targets separately; each must get real native implementations rather than a web-wrapper shortcut.

## Principles

Privacy and security before cloud sharing. Native experiences rather than wrappers. Original GoreeCloud product implementation with third-party technical dependencies correctly attributed. GC UI is the sole design authority. No paid subscriptions, network deployment, or unapproved sharing is necessary for this foundation.
