# GoreeCloud Tasks — Changelogs

**Record type:** Repository change history  
**Repository:** `GoreeCloud/tasks`  
**Lifecycle:** v0.1 Development / production not approved  
**Governing standard:** Standard — Repository Feature Tracking and Changelog Governance v1.0, effective September 22, 2026.

## 2026-09-22 — Repository feature/changelog governance migration

### Added

- `IMPLEMENTED-FEATURES.md` as the authoritative implemented-feature inventory.
- `PLANNED-FEATURES.md` as the authoritative planned/incomplete-feature inventory.
- `CHANGELOGS.md` as the authoritative repository change-history record.

### Changed

- Retired the repository `FEATURE-ROADMAP.md` control model.
- Removed the obsolete requirement to synchronize feature-roadmap authority with Google Drive.
- Kept the README as an operational/product overview while moving lifecycle feature authority into the dedicated repository-native records.

### Lifecycle boundary

This migration changes documentation/control-plane authority only. GoreeCloud Tasks remains v0.1 Development and production is not approved. Backup/recovery, notification operations, deployment, Release Candidate, Production Acceptance, and Stable qualification remain open.

## Historical change evidence

Historical implementation and validation evidence remains preserved by Git history, merged pull requests, CI/workflow records, repository documentation, migration history, and product-specific governed evidence. Future material integrated feature/change entries must be recorded here.

## Maintenance rule

Record material integrated changes here with enough exact repository evidence to distinguish authoritative `main` state from draft/unmerged work. Do not convert local/CI success into production deployment or Stable claims.