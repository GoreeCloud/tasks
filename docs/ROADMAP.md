# GoreeCloud Tasks — staged Fork-to-Native implementation

Each phase is an engineering workstream, **not a release promise**. The [proposed Tasks capability catalogue](https://docs.google.com/document/d/1yYzCPsShY6QkqJbJjFsUa25TASRiZ8Pk/edit) covers 18 functional areas; [capability traceability](CAPABILITY_TRACEABILITY.md) maps them to approved Waypoint naming and the owning implementation workstreams. **Catalogue inclusion is not implementation evidence.**

The [authoritative project specification](https://docs.google.com/document/d/1_z4T0hRNLrWFkDXmVTJLFe_mHumviM2B/edit) controls approved v0.1 scope. The [Waypoint identity standard](https://docs.google.com/document/d/1vBWITF3assryHSW4TH4oMKDIrmjDvqye/edit) controls capability-family semantics; Pulse means reminders/notifications/attention until separately revised.

## Foundation — partially implemented
- [x] Identify source, upstream SHA, AGPL/GPL obligations and existing destination.
- [x] Import upstream source into existing repository without upstream CI workflows.
- [x] Introduce product identity in core web navigation/title; separate third-party server-first desktop login.
- [x] Vendor pinned Glaze token CSS and an initial GoreeCloud theme mapping.
- [ ] Run representative functional, accessibility, security, API and UI regression validation.
- [ ] Finish official asset, icon, onboarding, settings, locale and upstream trademark review.

## Current priority: feature development

Feature delivery now takes priority over Todoist import. Focus first on everyday task management, the Glaze user experience, accessibility, reliability and data safety. The Todoist transition remains deferred until the core application is qualified.

The draft source includes Today quick capture with default Today deadlines, searchable cross-project Today/Upcoming/overview task lists, URL-preserved sorting, pagination, user-triggered refresh and accessible fetch retries. Search is debounced, clears with Escape, distinguishes no-results states and preserves filtering after a Today Quick Add, without remounting the list. Route-derived label IDs are validated and malformed label selections fail closed. Quick Add prevents overlapping saves, reports incomplete metadata or relationships without retrying uncertain batch creation, and waits for all parent/subtask relationship attempts to settle before surfacing partial failures. Duplicate task IDs in bulk API responses are treated as ambiguous and cannot create incorrect parent/subtask relationships. Quick Add preparation failures now have an English error message. Eight focused feature regression files passed 67/67 tests in an isolated checkout of executable revision `b9cf575`; Source Safety, Todoist guard, and Frontend Quality (TypeScript, focused tests, production build) CI passed on that exact revision. Backend readback/recovery, comprehensive suites, representative Glaze/browser accessibility and rollout acceptance remain open.


Latest Tasks feature work (October 10, 2026): Upcoming URL date expressions are now strictly validated before task-filter interpolation. Quick Add label and assignee writes now settle independently, preserve confirmed attachments and warn about incomplete details; new mixed-success/failure regression cases cover both labels and assignees. An account without projects can open project creation from Today, without flashing the action during initial project loading. Eleven targeted Quick Add/Today tests and focused Go bulk-creation/relation/label tests passed locally. The exact executable source revision `2e1856d` passed Frontend Quality, Source Safety and Go regression CI. Browser/Glaze accessibility, persisted-state readback, complete suites and release recovery remain pending.

## Core product rebuild — pending
- [ ] Redesign navigation, inbox/today/upcoming, projects, labels, filters and task editor as coherent Glaze experiences.
- [ ] Implement robust keyboard navigation, shortcut discovery, drag-and-drop, touch, contrast and reduced motion.
- [ ] Complete statuses, priorities, repeating tasks, dependencies, natural-language entry, reminders, search, notifications and bulk edits for GoreeCloud needs.
- [ ] Harden notification and background scheduling with explicit permissions and reliability.
- [ ] Establish API/DB contract tests and migration safety.

## Platform-native integration — pending
- [ ] GoreeCloud Identity, session protection, account and access boundaries.
- [ ] Wardveil Security and Policy authorization, secure configurations and threat reviews.
- [ ] Privacy Shield telemetry/data controls.
- [ ] Everkeep backup and tested restoration.
- [ ] Mesh, administration, observability and supported client integrations.
- [ ] Offline sync, conflict resolution, failure recovery and interoperability guarantees.

## Todoist transition — pending
- [ ] Export and reconcile the actual owner corpus, preserving every active task, recurrence, label, priority, subtask and reference.
- [ ] Test import idempotency, reversibility, incremental updates, privacy and data ownership.
- [ ] Pass Stable acceptance, then update authority governance in place and complete safe cutover.
- [ ] Preserve a rollback path; do not delete Todoist data during cutover.

## Waypoint capability streams — planning / not yet accepted

- [ ] **Capture / Focus / Horizon:** private Inbox, Today, Upcoming, Quick Add, priority semantics, due-timezone and recurrence UX; acceptance includes accessible capture and independent personal workspaces.
- [ ] **Projects / Together / Compass:** private/shared project memberships, role-based assignment, labels, filters, search, nested hierarchy, comments and audited changes; prove unauthorized access is denied.
- [ ] **Rhythm / Pulse / Timeline:** recurrence, reminders, notification delivery, timeline/Gantt and calendar interoperability; preserve authoritative task versus event ownership.
- [ ] **Operations / Trail / Archive:** optional P0–P4 operational metadata, source links, history/attribution, portable exports, backup/restore and recovery.
- [ ] **Cross-cutting security and accessibility:** Glaze UI, reduced motion, keyboard/touch/screen reader, authorization, confidential content separation and telemetry/AI minimization.
- [ ] **Post-v0.1 options:** AI-assisted extraction, advanced automation, offline/native clients, location reminders and analytics only after separate capability approval and threat/permission reviews.

**Open identity/licensing decisions:** the proposed document associates Pulse with analytics, while the approved identity associates it with reminders; keep the approved meaning. The ultimate original-native / AGPL-3.0-only target is **not yet** the current Vikunja-derived multi-license source tree. Do not prematurely relabel licenses or omit upstream attribution.

## Stable gate — pending
Build, unit/integration/e2e, accessible UI, real device, security/privacy, backup/restore, migration reconciliation, release artifacts, rollback and owner acceptance must all pass at an exact revision before production/Stable claims.
