# GoreeCloud Tasks — Planned Features and Open Obligations

**Record type:** Repository planned/incomplete-feature inventory  
**Repository:** `GoreeCloud/tasks`  
**Lifecycle:** v0.1 Development / production not approved  
**Authority:** Current `main` source, accepted repository evidence, and active GoreeCloud Tasks Management obligations  
**Governing standard:** Standard — Repository Feature Tracking and Changelog Governance v1.0, effective September 22, 2026.

## Interpretation

Items here are planned, incomplete, blocked, or acceptance-gated. Their presence does not imply implementation or release readiness. Partial foundations that already exist are also described in `IMPLEMENTED-FEATURES.md` for the verified portion only.

## Current stabilization obligations

- Complete the broader v0.1 acceptance requirements before production publication.
- Establish approved backup and isolated restoration validation for the eventual production environment.
- Verify production database migration, rollback, and recovery procedures against an exact candidate.
- Establish production scheduler/delivery operations for reminders without weakening per-user authorization and data minimization.
- Validate production ntfy or replacement notification-provider configuration, credential boundaries, rate limiting, failure handling, and recovery.
- Complete security/privacy review of multi-user authorization, archive import/export, collaboration, reminders, and operational metadata.
- Complete accessibility, responsive layout, performance, reliability, and user-flow acceptance against representative deployment/runtime conditions.
- Complete GLAZE UI V1.6 application-specific adoption and rendered/accessibility/performance/rollback acceptance where applicable.
- Evaluate and satisfy or explicitly justify all nine Integral Platform Systems: Manager, Privacy Shield, Wardveil Security, Everkeep, GLAZE UI, Mesh, Identity, Policy, and Observability. GoreeCloud Sync remains separately governed.
- Complete release packaging, deployment controls, rollback, Release Candidate, Production Acceptance, and Stable qualification.

## Product capability work still required

- Continue improving personal and shared task/project workflows beyond the verified v0.1 Development foundation.
- Expand operational GoreeCloud task metadata and related-record workflows only where authorization and lifecycle semantics remain explicit.
- Add further provider-neutral import adapters only with bounded validation and identity-safe migration rules.
- Expand portability/recovery while preserving ownership and collaboration authorization boundaries.
- Add production-grade notification delivery and scheduling after approved deployment authority exists.
- Improve administration/observability without exposing private task/project content to unauthorized operators.

## Explicit non-claims

Until corresponding evidence exists, this file does not claim:

- an approved production deployment;
- production backup/recovery acceptance;
- production notification/scheduler acceptance;
- complete Integral Platform System conformance;
- Release Candidate, Production Acceptance, or Stable status.

## Legacy Drive roadmap migration ledger — 2026-09-22

The retired Drive roadmap contained three `FR-*` control records. They are accounted for here so the source record can be retired without losing identifier-level traceability. These entries do not create duplicate task authority.

- **FR-001 — Roadmap reconciliation control.** Migrated into this file's interpretation, current obligations, and maintenance rule. The legacy requirement to keep a Drive roadmap synchronized is superseded by the repository-native governance standard.
- **FR-002 — Tasks Management routing control.** Preserved by the maintenance rule: actionable execution work belongs in GoreeCloud Tasks Management when required, with priority, dependency, and lifecycle state retained there rather than duplicated here.
- **FR-003 — Evidence and lifecycle control.** The evidence-backed state rule is preserved. The legacy repository/Drive synchronization clause is retired; lifecycle changes are now reconciled among `IMPLEMENTED-FEATURES.md`, `PLANNED-FEATURES.md`, `CHANGELOGS.md`, repository evidence, and Tasks Management as applicable.

This ledger is migration evidence only. It does not represent FR-001 through FR-003 as product features or as newly completed work.

## Maintenance rule

Move an item to `IMPLEMENTED-FEATURES.md` only after the authoritative implementation and required verification are integrated. Record material lifecycle changes in `CHANGELOGS.md`. Keep actionable execution work in GoreeCloud Tasks Management without creating duplicate task authority.