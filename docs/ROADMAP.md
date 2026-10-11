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

The draft source includes Today quick capture with default Today deadlines, searchable cross-project Today/Upcoming/overview task lists, URL-preserved sorting, pagination, accessible fetch retries and duplicate-title-safe multiline Quick Add. Search is debounced, provides a distinct no-results state and resets pagination. Task lists automatically load once authentication becomes ready. Quick Add prevents overlapping saves and reports incomplete labels, assignees or relationships without inviting duplicate full-batch retries. The five focused feature regression suites are now included in Frontend Quality CI and passed 50 tests in an isolated current-source checkout. Representative Glaze accessibility, backend readback/recovery and runtime acceptance remain open.

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
