# GoreeCloud Tasks — Architecture Decision Record

**Status:** Proposed target architecture plus verified early-source boundaries, October 31, 2026. This document does not claim deployment or Stable acceptance.

## Native clients

- **Web:** HTML/CSS/ECMAScript browser application, localStorage-backed development model. A served web application is the actual target here, not a substitute for OS-native clients.
- **Linux:** Python GTK4/libadwaita application, private XDG SQLite store with SQL constraints and parameter binding.
- **Android:** Kotlin Jetpack Compose application, private SQLiteOpenHelper-based local database with no Internet permission.
- **Design:** GC UI Canvas/Surface/Lens principles, semantic color and native platform controls. Formal visual acceptance remains pending.

## Storage and data ownership

The three stores are deliberately isolated. This prevents advertising synchronization or shared-state guarantees before a secure protocol, authentication, conflict management, server ownership, and migrations are in place. No device data is uploaded by these clients in the foundation.

The `Task` contract at the product boundary will eventually include a globally unique ID, title, Markdown details, project/section hierarchy, labels, priority 1–4, scheduling and deadline fields, recurrence, assignments, completion state, actor/event metadata, revision and tombstone. Existing minimal local schemas are *not* the final wire contract.

Do not merge local stores or import actual private task data without migration tooling, recovery validation and explicit acceptance.

## Planned self-hosted service

A future GoreeCloud Tasks backend should expose versioned HTTPS APIs for authenticated workspace operations; enforce organization/project authorization on **every** data access; use server-generated monotonically ordered change records, tombstones, idempotent mutations, and deterministic conflict resolution. PostgreSQL is a suitable primary shared store. The final backend selection and deployment are pending operational review.

Separate secrets from source and public CI. Use short-lived access tokens, revocation, encrypted transport, rate limits, request validation, audit events, and safe file handling. Do not enable cross-origin public APIs or unprotected network endpoints by default.

## Offline-first synchronization acceptance gate

Before connecting clients, define and test:
1. Stable schema versioning and reversible migrations.
2. Authenticated per-workspace authorization with denial tests.
3. Device identity and renewable sessions.
4. Idempotent mutations and ordered cursor-based pull.
5. Deletions as tombstones, retries, and duplicate prevention.
6. Conflict rules for simultaneous edits/completions and recurrence.
7. Encryption, attachments, retention, and backup/restore drills.
8. Observability without exposing task text in logs.
9. Multi-device tests across offline, restart, clock skew, and reconnect.
10. Todoist export/import reconciliation without treating migration as accomplished.

## Native release and user safety

Linux packaging, desktop integration, notifications, permissions, accessibility and update/rollback must be tested. Android debug compilation must be followed by install/launch, notification and lifecycle/backup tests, signed release planning, and secure APK handoff under `GoreeCloud/Artifacts`. Native code alone does not establish supported, installed or Stable release status.
