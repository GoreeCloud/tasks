# GoreeCloud Tasks — staged Fork-to-Native implementation

Each phase is an engineering workstream, **not a release promise**.

## Foundation — partially implemented
- [x] Identify source, upstream SHA, AGPL/GPL obligations and existing destination.
- [x] Import upstream source into existing repository without upstream CI workflows.
- [x] Introduce product identity in core web navigation/title; separate third-party server-first desktop login.
- [x] Vendor pinned Glaze token CSS and an initial GoreeCloud theme mapping.
- [ ] Run representative functional, accessibility, security, API and UI regression validation.
- [ ] Finish official asset, icon, onboarding, settings, locale and upstream trademark review.

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

## Stable gate — pending
Build, unit/integration/e2e, accessible UI, real device, security/privacy, backup/restore, migration reconciliation, release artifacts, rollback and owner acceptance must all pass at an exact revision before production/Stable claims.
