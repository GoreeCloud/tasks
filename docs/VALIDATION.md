# Exact-revision verification record

## Pinned foundation
- Vikunja upstream source: `6263ff12956f29bd84ed1346d9752f82e02cdd59`.
- Glaze token source: `GoreeCloud/glaze@0798de28fe0626d6cc8bd7986dc9c4b922119c35`.
- Verified frontend CI candidate (source + CI): `e08c6e4609da3404ecc95e7ed4f9cd9bac20cede`.
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
