# GoreeCloud Tasks — Implemented Features

**Record type:** Repository implemented-feature inventory  
**Repository:** `GoreeCloud/tasks`  
**Lifecycle:** v0.1 Development / production not approved  
**Authority:** Current `main` source and accepted repository evidence  
**Governing standard:** Standard — Repository Feature Tracking and Changelog Governance v1.0, effective September 22, 2026.

## Interpretation

This record describes capabilities present in the current GoreeCloud Tasks Development implementation. It does **not** establish production deployment, accepted production backup/recovery, Release Candidate, or Stable qualification.

The README remains an operational/product overview. This file is the lifecycle authority for what is implemented.

## Implemented Development capabilities

### Accounts, privacy, and authorization

- Custom Django user model established before the first application migration.
- Individual accounts and private personal task boundaries.
- Private and explicitly shared projects.
- Project Manager, Member, and Viewer roles.
- Exact-username project membership administration with revocation that preserves membership history.
- Automatic membership revocation when a shared project becomes private.
- Authorization-aware task/label query helpers and server-side mutation checks.
- Historical creator/assignee retention after access revocation while new relationships require current authorization.
- Read-only Viewer presentation and authorization-scoped task/project access.
- Django admin limited to account administration; private task/project/label content is not registered there.

### Task and project workflows

- Project list, creation, detail, and owner-controlled settings.
- GoreeCloud P0-P4 priorities with lifecycle status kept separate.
- Task creation through Quick Add and the full editor.
- Task editing, completion, reopening, and deletion.
- Inbox, Today, Upcoming, and authorization-scoped Search views.
- Project-aware Quick Add and full task creation constrained to editable projects.
- Personal and project-scoped labels with server-side scope enforcement.
- Subtasks implemented as normal task records within the parent authorization scope.
- Authorized task detail pages with labels, subtasks, comments, activity, and optional operational metadata.
- User-attributed comments for users with task edit access.
- Material task/project activity records with acting-user attribution.
- Data-minimized task edit history recording changed field keys rather than duplicating private content.

### GoreeCloud operational metadata

- Initial systems, services, environments, workload categories, blockers, resume conditions, operational prerequisites, and related-record metadata.
- Search over authorized task content and implemented operational dimensions after authorization scoping.

### Reminders and ntfy Development boundary

- Private user-specific reminder records with preferences, lead time, local time-zone handling, delivery state, cancellation, and retry metadata.
- Reminder scheduling for readable open tasks without expanding Viewer edit authority.
- Delivery-time authorization re-checks that cancel pending reminders after access revocation.
- Pending-reminder cancellation when the task is completed/cancelled.
- Non-identifying generated per-user ntfy topics.
- Dedicated ntfy publication boundary using environment/file-backed service credentials.
- Data-minimized reminder messages.
- `send_due_reminders` scheduler boundary without claiming production scheduler deployment.
- Disposable least-privilege authenticated ntfy integration validation in CI.

### Portability, import, and recovery foundations

- Versioned authenticated JSON exports for user-owned data and owner-only project archives.
- Schema-v2 user archives preserving notification preferences and in-scope reminders.
- Backward-compatible schema-v1 user-archive restoration for earlier core application data.
- Export scope that does not turn shared-project visibility into bulk export authority over another user's project.
- Source-neutral external-import records and atomic import execution validating relationships before writes.
- Full-fidelity guarded user-archive restoration with exact username resolution, collaborator-account requirements, clean-target enforcement, relationship validation, historical membership preservation, and atomic reconstruction.
- Authenticated portability recovery controls with explicit confirmation, UTF-8 JSON parsing, 25 MiB upload limit, and private/no-store responses.
- Verified-format Todoist project CSV migration for tasks, subtasks, project labels, notes/comments, priorities, and conservative schedule metadata.
- Todoist author/responsible values preserved only as source metadata and never promoted into GoreeCloud identities.

### Runtime and repository foundation

- PostgreSQL-ready application configuration with SQLite for isolated tests.
- File-based secret support for the non-root application container.
- Dockerfile and Docker Compose Development stack.
- Loopback-only Development web-port publication and no published database port.
- Non-sensitive `/health/` endpoint.
- CI for Django configuration, migration drift, application tests, image build, PostgreSQL-backed migrations, Compose startup, live health verification, and disposable ntfy integration validation.
- AGPL-3.0-only license selected for the original GoreeCloud Tasks application.

## Implemented-but-not-accepted boundaries

The following foundations exist but remain acceptance-gated and therefore also appear in `PLANNED-FEATURES.md`:

- User archive restoration without accepted production backup/isolated restore operations for the eventual production environment.
- ntfy integration without an approved production scheduler/delivery deployment.
- Docker/PostgreSQL runtime foundations without production deployment acceptance.
- Multi-user authorization foundations without overall Stable qualification.

## Maintenance rule

When an obligation in `PLANNED-FEATURES.md` becomes implemented and verified on the authoritative integration line, reconcile it here and record the material change in `CHANGELOGS.md`. Draft or unmerged pull requests are not implementation authority.