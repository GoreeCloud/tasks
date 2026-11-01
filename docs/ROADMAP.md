# GoreeCloud Tasks — Feature and Release Roadmap

**Stage:** Early development. The user's complete 16-category product specification is the product destination, not an inventory of implemented features.

## A. Foundation (in progress)

- [x] Public `GoreeCloud/tasks` repository initialized with first-party web, Linux, Android sources.
- [x] Device-local task creation, completion, reopening, deletion, and P1–P4 priorities in all three clients (source implemented; verification tracked separately).
- [x] Web inbox/project creation, date entry, search, completed history, themes, validated JSON export/restore and stale-tab write protection (source; comprehensive recovery validation pending).
- [x] Linux GTK and Android Compose projects (source).
- [x] Linux project creation/assignment, task view filters, due date capture and local search (source; GUI and device validation pending).
- [x] Linux user-local desktop integration scripts and icon, with isolated install/uninstall test preserving local task data; distro acceptance pending.
- [x] Browser-compatible schema-1 Linux JSON export and guarded empty-store import via CLI and native GTK file dialogs, with round-trip tests; full native recovery acceptance pending.
- [x] Android native project creation/assignment, due-date picker, Today/Upcoming/Project filters and non-destructive schema v2 migration (source; device verification pending).
- [x] Android schema-v3 completion metadata and native system-document export of portable schema-1 JSON; legacy completion metadata fails closed, import and real-device validation remain pending.
- [x] Android task-editing dialog for title, priority, due date and project with pure validation unit tests (source; device verification pending).
- [x] Hardened text/priority validation and portable backup boundary cases across native clients; Android verification relies on CI/device tests.
- [ ] Verify all platform builds and runtime operation, fix defects, audit accessibility and GC UI appearance.
- [ ] Desktop packaging, Android device validation, and standalone APK handoff if requested.

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
