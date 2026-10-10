# GoreeCloud Tasks — proposed capability traceability

> **Status: Proposed feature catalogue / planning aid, not implemented-feature certification.**
> **Product:** GoreeCloud Tasks · **Capability identity:** GoreeCloud Waypoint · **Presentation:** GoreeCloud Tasks — Powered by Waypoint
> **Scope:** Privacy-first, self-hosted, multi-user task, project and operational work management.

## Authoritative sources and precedence

- **Feature proposal:** [GoreeCloud Tasks — Features and Capabilities — Proposed.docx](https://docs.google.com/document/d/1yYzCPsShY6QkqJbJjFsUa25TASRiZ8Pk/edit) (October 10, 2026; GoreeCloud Drive / Projects). The source catalogue retains all **18** capability areas, Waypoint domains, product principles and the intended outcome.
- **Product specification:** [Project Specification — Tasks.docx](https://docs.google.com/document/d/1_z4T0hRNLrWFkDXmVTJLFe_mHumviM2B/edit). The project specification, applicable governance and approved standards control release scope and requirements if a proposal disagrees.
- **Approved capability naming:** [Standard — Waypoint Identity.docx](https://docs.google.com/document/d/1vBWITF3assryHSW4TH4oMKDIrmjDvqye/edit). Waypoint is a **capability identity within Tasks**, not a separate service, task engine, database, authorization boundary, or replacement product.
- **Verified software state:** [current repository](https://github.com/GoreeCloud/tasks), [draft implementation PR #1](https://github.com/GoreeCloud/tasks/pull/1), [validation evidence](VALIDATION.md), [roadmap](ROADMAP.md), and [Todoist migration gate](TODOIST_MIGRATION.md). A feature listed in an upstream/fork codebase is **not** certified as a GoreeCloud production capability.

This document is a crosswalk, **not a second feature catalogue or a declaration of acceptance**. Update the proposed Drive catalogue or governing specification through their own authorized processes instead of silently altering their meaning here.

## Waypoint family crosswalk

| Approved Waypoint family | Proposed catalogue sections | Scope to qualify | Working track |
|---|---|---|---|
| **Capture** | §1 Core Tasks; §10 AI; §13 Import | Inbox, Quick Add, accessible capture, imports and human-reviewed extraction | UI #2; migration #4 |
| **Focus** | §1 Core Tasks; §4 Views; §9 Productivity | Today, attention/priority, focused execution, keyboard quick actions | UI #2 |
| **Horizon** | §2 Scheduling; §4 Views; §12 Calendar | Upcoming, time zones, planned vs firm dates and future workload | UI #2; backend #3 |
| **Projects** | §3 Projects; §4 Views; §6 Relationships | Private/shared projects, sections, boards, task hierarchy and dependency model | UI #2; backend #3 |
| **Rhythm** | §2 Scheduling; §9 Productivity; §11 Automation | Recurrence, interval/weekday semantics and scheduled routines | UI #2; backend #3; migration #4 |
| **Pulse** | §8 Notifications; §9 Productivity | **Canonical:** reminders, notifications, deadlines and attention signals; proposed reporting and scores need separate product-family adjudication | UI #2; backend #3 |
| **Compass** | §5 Search; §4 Views; §10 AI | Search, relative/compound filters, saved views and authorized AI-assisted search | UI #2; backend #3 |
| **Together** | §7 Collaboration; §15 Identity/Privacy | Private/shared boundaries, membership, role/permission enforcement, comments and attribution | backend #3; UI #2 |
| **Operations** | §17 Operational Work; §6 Dependencies; §18 Governance | Optional GoreeCloud P0–P4, resources, blockers, prerequisites, evidence and change references | backend #3; UI #2 |
| **Timeline** | §2 Scheduling; §4 Gantt/Timeline; §6 Dependencies; §12 Calendar | Planning, dependency visualization, approved Calendar interoperability without authority confusion | UI #2; backend #3 |
| **Trail** | §7 Collaboration; §9 History; §15 Security; §18 Reliability | Attribute-level history, attribution, permission-aware audit trails | backend #3 |
| **Archive** | §13 Portability; §1 History; §18 Data Protection | Completion history, structured exports, reversible import, backup/recovery and retention | backend #3; migration #4 |

**Important identity variance:** the *proposed catalogue* groups task progress, productivity, activity and reporting under Waypoint Pulse. The **approved Waypoint Identity standard** assigns Pulse primarily to reminders, notifications, deadlines and attention signals. Continue using the approved definition in product navigation and identity until the governing standard is explicitly revised. Productivity analytics may remain in the functional backlog without silently repurposing the identity.

## Operational priority-model decision boundary

The [currently approved **Priority Levels v0.1**](https://docs.google.com/document/d/1Rmno94uTFzQK4KrpaImT0QcZRgTc5CMC/edit) defines **P0 Critical, P1 Urgent, P2 High, P3 Standard, P4 Low**, consistent with the proposed Tasks catalogue. A separate [**v0.2 replacement candidate**](https://docs.google.com/document/d/1EjJoQdp-ggf1BwaMse_K32lh8dJy-4sy/edit) proposes **P0–P6**, but its candidate status does **not** authorize new numeric meanings, database migrations, UI defaults or imports. The [existing migration issue #70](https://github.com/GoreeCloud/tasks/issues/70) and Todoist qualification task track adoption and safe semantic preservation. Until the candidate is formally adopted with reconciled source/destination mappings and tested rollback, **retain v0.1 P0–P4 semantics** and do not silently reinterpret P3 or P4.

## Capability families beyond a single Waypoint domain

| Catalogue area | Governing engineering requirement | Scope/verification |
|---|---|---|
| §14 Applications, UI and accessibility | Glaze conformance, keyboard/screen-reader/touch/reduced-motion/contrast, responsive web | Native mobile and desktop platform expansion not assumed in initial release |
| §15 Identity, security and privacy | User account isolation, scoped access, secure APIs, auditability, no administrator-by-default private content access | Review sharing, sessions, roles, attachments and secrets before deployment |
| §16 Hosting, infrastructure and development | Supported containers, migration safety, CI/API tests, release provenance and licenses | Initial Docker/Compose development; production not authorized by repository presence |
| §18 Reliability, governance and data protection | Readback reconciliation, backup/restore, recovery, retention, integrity and rollback | Exact-source Stable acceptance required before task-authority cutover |
| §10 AI and §11 Automation | Opt-in/scoped permissions, user review and consequential-action confirmation | No autonomous infrastructure modification or unrestricted task mutation |
| §12 Integrations | Application-level API contracts and system-specific authority | External calendars/issues/records remain authoritative in their own systems |

## Delivery phases and non-goals

**v0.1 foundation requirement (from project specification; still unverified as a release):** multi-user separation; private Inbox/Today/Upcoming; projects, membership and assignments; task editing and P0–P4 operational extensions; labels, subtasks, search, Quick Add, responsive task detail, shared-task comments, activity, authz, health, Docker/Compose, test/CI, portable export foundation and recovery requirements.

**Subsequent qualification tracks:** advanced Gantt/timeline, custom recurrence semantics, high-fidelity calendar sync, automation, AI extraction, advanced reports, expanded views, offline conflict recovery, native clients, optional location reminders and extensions. Prioritization is **not** final approval or an implementation claim.

**Explicit initial-scope exclusions:** native Android/iOS, public anonymous project sharing, plugin marketplace, autonomous infrastructure changes, and unrelated commercial billing/enterprise functionality are not required for the first release.

## Progress, evidence and approval rules

1. Mark every newly selected feature as **proposed**, **approved-for-implementation**, **in progress**, **implemented/source-verified**, **tested/verified**, or **release-accepted** separately. Only actual evidence may advance a status.
2. Validate ordinary personal/family workflows independently of optional GoreeCloud infrastructure-specific fields.
3. For shared work, prove cross-user private-data isolation, task-comment/assignment permissions, auditing and account-lifecycle behavior.
4. Verify safe failure, idempotency, source IDs, recurrence/date/zone fidelity, attachment/comment preservation, backup/restore and destination readback for migration. **Never move task authority merely because a build or package test is green.**
5. Retain legal provenance: **the current inherited code is not yet the original-only, AGPL-3.0-only target** described by the long-term specification. Preserve inherited Vikunja and other license notices pending source replacement and distribution clearance.
6. Record decisions in the owning specification/standard, implementation in GitHub, and unfinished task obligations in Todoist Free (with original legacy records retained until reconciled). Do not create competing authoritative status registers.

## Workstream links

- [#2 — Glaze UI, primary views and accessibility](https://github.com/GoreeCloud/tasks/issues/2)
- [#3 — backend, roles/permissions and GoreeCloud integration](https://github.com/GoreeCloud/tasks/issues/3)
- [#4 — zero-loss Todoist migration and Stable transition](https://github.com/GoreeCloud/tasks/issues/4)
- [Draft PR #1 — incremental fork-to-native foundation](https://github.com/GoreeCloud/tasks/pull/1)

**No Stable claim, production deployment, live Todoist migration, ownership transfer or canonical Waypoint identity change is authorized by this traceability document.**
