# Exact-revision verification record

## Pinned foundation
- Vikunja upstream source: `6263ff12956f29bd84ed1346d9752f82e02cdd59`.
- Glaze token source: `GoreeCloud/glaze@0798de28fe0626d6cc8bd7986dc9c4b922119c35`.
- Earlier foundation CI candidate (source + CI): `e08c6e4609da3404ecc95e7ed4f9cd9bac20cede`.
- GitHub Actions evidence: [Frontend Quality](https://github.com/GoreeCloud/tasks/actions/runs/38077625721) and [Source Safety Baseline](https://github.com/GoreeCloud/tasks/actions/runs/38077625712).

## Completed checks on the verified candidate

| Check | Outcome | Evidence and scope |
|---|---|---|
| Upstream source import | Pass | GitHub readback confirms pinned provenance, public development branch and source files |
| License files | Pass at file-presence level | AGPL root/frontend, GPL desktop and MIT Glaze license retained; complete distribution audit still required |
| Upstream GitHub workflows | Excluded | Only GoreeCloud-authored source-safety and frontend-quality workflow files are active |
| Source-safety workflow | Pass | GitHub Actions exact-head green result for `e08c6e4` |
| Frontend dependencies | Pass | Frozen-lockfile install with lifecycle scripts disabled on GitHub Actions; lockfile still requires routine security review |
| Vue/TypeScript typecheck | Pass | GitHub Actions exact-head TypeScript check |
| Wordmark unit tests | Pass | 2/2 `Logo.test.ts` on GitHub Actions |
| Production frontend bundle | Pass | GitHub Actions production build step |
| Web document title | Source verified | `frontend/index.html` title; manual browser smoke test pending |

## 2026-10-10 Fork-to-Native enhancement validation

Latest reviewed **frontend source revision**: `4c566dffdef344be4a701912f2fb2f350780a686`.

- **Passed, exact revision:** [Frontend Quality](https://github.com/GoreeCloud/tasks/actions/runs/38081984129), including frozen dependency installation, Vue/TypeScript check, wordmark tests, newly added API server/privacy regression tests, and production frontend bundle.
- **Passed, exact revision:** [Source Safety Baseline](https://github.com/GoreeCloud/tasks/actions/runs/38081984231).
- **Committed source changes:** stricter HTTP(S) API URL validation and rejection of embedded credentials, redacted connection warnings, a Glaze-based login/onboarding visual, an internal About path with explicit Vikunja attribution, keyboard-operable sidebar resizing, and updated English interface strings.
- **Local validation limitation:** developer-laptop typecheck and Vitest attempts became unresponsive under extreme RAM/swap pressure; do not count their outcomes as passes. The independent GitHub Actions results above are authoritative for the exact source revision.
- **Scope exclusion:** these checks do **not** establish backend/database acceptance, manual rendered UI inspection, accessibility audit, integration completeness, user-data migration, offline behavior, or Stable readiness.

## Additional exact-head validation — October 10

- Code head `ca39536bb40b681a49fdee22f7c2e3666405c416`.
- [Todoist importer Go unit/regression CI: PASS](https://github.com/GoreeCloud/tasks/actions/runs/38083056204).
- [Frontend typecheck, targeted tests and production bundle: PASS](https://github.com/GoreeCloud/tasks/actions/runs/38083059656).
- [Source Safety Baseline: PASS](https://github.com/GoreeCloud/tasks/actions/runs/38083059710).
- Migration now guards incomplete source graphs, child task metadata, unsupported nested projects, missing recurrence mappings and unsupported project-note attachments. It is **not** a complete dry-run importer, zero-loss migration, or validated task authority.
- Error diagnostics now disable replay and performance sampling, and minimize captured resource URLs. Backend-wide security, full importer reconciliation, attachments, database and recovery gates remain open.

## Continued October 10 migration integrity checks

At code revision `d51cd8f5a41cdeff34f62d86021ceb23e174bc7d`, the focused [Todoist Import Integrity](https://github.com/GoreeCloud/tasks/actions/runs/38091911889) and [Source Safety](https://github.com/GoreeCloud/tasks/actions/runs/38091911912) workflows passed.

- Nested project parent references preserve multi-level source ancestry, including child-first exports.
- Preflight rejects missing/cyclic project parents and missing or opaque task-note attachment locations.
- Bounded, SSRF-safe downloads fail conversion on HTTP errors, missing bytes or oversize files instead of losing attachments silently.
- The migration screen warns that imports require source/destination reconciliation and are not live sync.
- **Unverified:** actual persisted multi-level hierarchy, task-note author/comment semantics, reversible/idempotent live importer, full end-to-end database and device testing, exact source→destination reconciliation and Stable acceptance.

## October 10 — pre-insertion record-count and completeness checks

Source code at `0ef110ee68fb6db59719b63fff896c9dc4a7bfab` extends the Todoist importer:

- A metadata-only comparison checks counts of projects, sections, tasks, subtasks, reminders and attachments between the validated Todoist snapshot and converted model **before database insertion**.
- Whitespace-only titles and truncated task-note snapshots are now rejected rather than silently dropped.
- Missing OAuth access tokens or inaccessible completed-task detail records fail import explicitly; OAuth error response bodies are not propagated into logs or error strings.
- Regression tests inject dropped projects, sections, tasks, subtasks, reminders and attachments to demonstrate count failures.
- Verified focused Go test and source-safety results for this **code revision**: [Todoist Import Integrity](https://github.com/GoreeCloud/tasks/actions/runs/38092487341) and [Source Safety Baseline](https://github.com/GoreeCloud/tasks/actions/runs/38092487210), both passed. Frontend Quality is a separate gate, not implied by these checks.

**Not established:** a live or read-only Todoist dry run, persisted source-ID map, imported note/comment metadata fidelity, post-insert destination readback, exact corpus reconciliation, database recovery/rollback, Stable acceptance or authority cutover.

## October 10 — Waypoint capability catalogue and About presentation

- **Reviewed source revision:** `dca6cb431bf28cfa0e388a3619795660524a0595`.
- **Exact-head PASS:** [Frontend Quality](https://github.com/GoreeCloud/tasks/actions/runs/38093414327) (pinned package install, Vue/TypeScript check, `Logo.test.ts`, new `About.test.ts`, URL/privacy tests and production frontend build).
- **Exact-head PASS:** [Todoist Import Integrity](https://github.com/GoreeCloud/tasks/actions/runs/38093414263) (focused Go importer regressions).
- **Exact-head PASS:** [Source Safety Baseline](https://github.com/GoreeCloud/tasks/actions/runs/38093414268).
- **Documentation:** [proposed 18-section catalogue](https://docs.google.com/document/d/1yYzCPsShY6QkqJbJjFsUa25TASRiZ8Pk/edit) recorded as a Word document in the authorized GoreeCloud Drive account; `docs/CAPABILITY_TRACEABILITY.md` maps the proposal to the approved Waypoint identity and issues #2, #3 and #4.
- **UI:** About displays “GoreeCloud Tasks — Powered by Waypoint” and retains Vikunja provenance attribution. The feature-catalogue mapping does **not** represent delivery of unimplemented analytics, native apps, AI automation, cross-system integrations or operational authorization.
- **Documented variance:** the proposed catalogue uses Pulse for productivity and reporting; the approved Waypoint identity standard assigns Pulse to reminders and notification signals. The approved meaning remains controlling pending any authorized decision.
- **Still pending:** actual rendered UI/assistive-technology acceptance, full backend/security/license conformance, 100% post-migration reconciliation, backup/restore, native architectural replacement, Stable qualification and live task authority cutover.

## Open acceptance gates

| Check | Required evidence | Status |
|---|---|---|
| All frontend unit/lint/e2e tests | Representative workflow and regression passing on exact source | Pending |
| Go backend/API and data migrations | Build, unit/API, DB migration and upgrade/rollback tests | Pending |
| Authentication, authorization and privacy | Thorough threat model, relevant security tests, default telemetry audit | Pending |
| Glaze V1.7 Stable consumer conformance | Accessible design, contrast, keyboard/touch, reduced motion, responsive and manual acceptance | Pending |
| Official assets and full UI rebuild | Approved identity and complete inherited trademark audit | Pending |
| Platform integration | Identity, Policy, Wardveil, Privacy Shield, Everkeep, Mesh, observability where applicable | Pending |
| Offline/reconnect and recovery | Reproducible conflicts, backup/restore, recovery and resilience tests | Pending |
| Todoist and legacy zero-loss migration | Verified real corpus, complete source-to-destination reconciliation and rollback | Pending |
| Release and production acceptance | Exact revision, artifact attestation, owner acceptance and in-place authority cutover | Pending |

**Boundary:** Passing the initial build and targeted automated checks demonstrates only a source/build foundation. It does not establish full feature parity, production readiness, native architecture, Glaze consumer conformance, task authority, or Stable status.
