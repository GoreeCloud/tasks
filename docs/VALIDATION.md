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

## October 10 — Todoist calendar fidelity and import consent

**Verified code revision:** `000dcb66655a86cbb844cbc18edd3ddc8d44e458`.

- **Backend:** Discontinued the unsafe approximation of calendar months/years as 30/365-day fixed intervals; such Todoist recurring schedules now fail preflight rather than change cadence. Added source note, project-note and reminder identity checks and a note/project consistency check.
- **Frontend:** Todoist OAuth authorization no longer automatically starts a migration. The import screen requires user acknowledgement of backup and duplicate risks before submitting; repeat imports demand fresh authorization/acknowledgement. A pure consent guard has four focused unit-test cases added to the frontend CI selection.
- **Exact-code Go import regression result:** [Todoist Import Integrity — PASS](https://github.com/GoreeCloud/tasks/actions/runs/38094172766).
- **Exact-code Source Safety result:** [Source Safety Baseline — PASS](https://github.com/GoreeCloud/tasks/actions/runs/38094175293).
- **Frontend Quality:** Pending at the time this entry was authored; assess the final exact-head workflow before claiming passed. The new consent copy is temporarily inline English after connector update of the inherited large translation JSON was blocked; localization remains an open accessibility/UX acceptance task.

These are **pre-import fail-closed improvements**; they do not prove post-insertion data preservation, locale completeness, safe live Todoist migration, full calendar-timezone fidelity, backup/restore or Stable acceptance.

## October 10 — Todoist upstream response and pagination integrity

**Reviewed source revision:** `f6fa9ac4bbcf8550120d4feb2101b2b0c9a2a5de`.

- **Implemented:** A shared Todoist HTTP decoder now refuses non-2xx responses before accepting OAuth, full sync, completed task pages/details and archived project pages/details. Every response body is closed on success and error. Errors identify the stage without copying upstream bodies or URLs.
- **Implemented:** Completed-task and archived-project pagination use independent cursor sets and stop on a repeated cursor, preventing an unbounded repeated-page loop from appearing successful.
- **Focused test coverage:** Successful and malformed JSON, 301 redirects, 401 authentication failures, 429 rate limits, 500 errors, missing response, response body closure, sensitive error-body non-disclosure and cursor-repeat detection.
- **Exact-head Todoist Import Integrity: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38094918071
- **Exact-head Source Safety Baseline: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38094918075
- **Frontend Quality:** source has not changed from the previously passing frontend implementation; the exact-head workflow remains to be checked before any complete-checks claim.
- **Limitations:** Responses may still need source-snapshot completeness, semantic task/comment/attachment fidelity, transactional insert, idempotency, readback reconciliation, CSRF/state binding, authorized test import and rollback evidence. No Todoist live data was accessed or imported.

## October 10 — completed-task identity, deleted projects and OAuth fallback

**Verified code revision:** `e2ccb60d2d44a26b3d78714de344535ca7dea765`.

- **Source-page integrity:** Completed task pages must have non-null task records, identifiers, project references and completion timestamps. Nil project metadata is rejected; returned detail records must match the source task and project IDs. Archived project pages reject nil/unnamed IDs and duplicate project IDs.
- **No silent omission:** A completed item associated with a deleted source project is rejected rather than skipped; this is a fail-closed safety decision pending a supported preservation mechanism.
- **OAuth defense-in-depth:** A cryptographic random-state generation failure no longer falls back to a fixed state; the authorization URL is not issued. The auth URL encodes query parameters. **OAuth callback state validation and anti-CSRF binding remain absent** and require separate implementation and testing.
- **Go CI:** [Todoist Import Integrity — PASS](https://github.com/GoreeCloud/tasks/actions/runs/38095428885) at this code revision, including newly added page/detail/OAuth regressions.
- **Source safety:** [Source Safety Baseline — PASS](https://github.com/GoreeCloud/tasks/actions/runs/38095428912) at this revision.
- **Frontend:** Exact-revision check under evaluation as of initial documentation; do not treat pending work as passed.
- **Not demonstrated:** Actual API response compatibility with representative authenticated Todoist archives, full source fidelity, a validated OAuth callback, persistence reconciliation, rollback, or Stable readiness.

## October 10 — confirmed Todoist initial full snapshot

**Validated code revision:** `67ede9b63513accf746d9c4840034208f55b21a8`.

- **Implemented:** The initial `sync_token="*"` API response must confirm `full_sync: true`, contain a nonblank returned synchronization token, and explicitly contain the seven source resource arrays used by the importer. JSON null or absent arrays are rejected; explicit empty arrays are accepted.
- **Focused regressions:** Nil/incremental/missing-token snapshots, absent individual collections, incomplete JSON that looks like an empty account, and valid full empty snapshots. Added additional preflight tests for missing/reused note, project-note and reminder IDs.
- **Go Todoist Import Integrity PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38096438050 at this exact code revision.
- **Source Safety Baseline PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38096442282 at this revision.
- **Limitation:** Todoist documentation warns that initial full syncs may lag for large accounts. **Full-sync confirmation does not establish freshness or atomic consistency.** An incremental catch-up, account/source consistency validation, archived/completed scope coverage, record-level destination readback, backup/rollback, and representative provider API tests are still required before live import. Frontend check must be verified separately on the final head.

## October 10 — user-bound Todoist OAuth state and explicit consent

**Verified source revision:** `938d0849b97b5de19b1961651060aa1020a273d6`.

- **Server:** The Todoist auth URL now requires the authenticated destination user and contains a signed state binding that user, a random nonce, and an issuance timestamp. An invalid/expired/cross-user state is refused by the shared migration handler **before** a migration claim or dispatch, including direct calls to the migrate API.
- **Client:** A browser-tab-scoped challenge is recorded from the Todoist authorization URL and is consumed when the OAuth callback arrives. Absent or mismatched callbacks cannot reach the consent screen; even successful callbacks cannot auto-import. The code and validated state are submitted together.
- **Language readiness:** English consent and authorization-error strings moved to the source translation catalog; other locales still require translations.
- **Go importer + handler tests PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38097125070
- **Frontend typecheck + targeted Vitest + bundle PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38097125089
- **Source Safety Baseline PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38097125134
- **Limitations:** Stateless backend signatures do not implement durable nonce consumption/revocation; same-user replay within the validity window still needs threat-model review. Representative Todoist OAuth provider flows, cross-tab/browser login transitions, proxy compatibility, session expiry, domain and time skew, actual task migration, rollback and full-data reconciliation remain unverified.

## October 10 — strict paginated responses and callback URL hygiene

**Verified source revision:** `d6f02afa4d9ba3700bc8b82b8d65e65408241db9`.

- **Backend source fidelity:** Todoist completed-task listing pages require an explicit `items` array, and archived-project listing pages require an explicit `results` array. JSON `null`, `{}`, or missing/null collections fail rather than masquerade as accounts with zero source records; explicit empty arrays remain valid.
- **HTTP response integrity:** The Todoist decoder requires a single complete JSON value. Trailing garbage or appended JSON documents are rejected without copying private upstream response content into diagnostics. Response bodies close even when parsing fails.
- **Frontend privacy:** The Todoist OAuth code and signed state are captured then removed from the browser address bar before any awaited status or authorization call. Mounted tests verify URL cleanup for accepted and rejected callbacks; signed user binding and explicit consent remain required.
- **Exact-revision Go importer + handler tests: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38097857423
- **Exact-revision Frontend Quality: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38097857440
- **Exact-revision Source Safety Baseline: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38097857411
- **Unverified:** Representative real-provider API compatibility, complete task/comment/attachment fidelity, post-insertion persistence readback, source snapshot freshness, OAuth nonce revocation, import idempotency, backup and rollback. No owner-data import or release authority transfer was performed.

## October 10 — Todoist due-date and unsupported source-resource safety

**Implementation revision:** `92c3938e95540f2a3112c1d5cc706c4aa62d7fb3`.

- **Timestamp semantics:** Fixed instants now parse RFC3339 with numeric UTC offsets and fractional-second precision. Floating local-time timestamps are explicitly rejected by preflight for tasks and reminders until Todoist's source user timezone and destination floating-time semantics can be preserved. Malformed date values and unsupported timezone metadata reject instead of shifting task deadlines. All-day dates continue to use existing end-of-day conversion and require calendar fidelity review.
- **Unsupported resource detection:** Location reminders and saved location collections are decoded from the source Sync response. Any nonempty data, plus shared projects whose collaboration/permissions cannot be preserved, aborts before destination writes.
- **User-facing restrictions:** English Todoist migration warning now lists floating local times, geo reminders, saved locations, and shared projects as blocked source features; no silent source-data omission is presented as successful.
- **Focused Go importer + handler tests PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38098549529
- **Source Safety Baseline PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38098549535
- **Frontend Quality:** confirm at final revision; https://github.com/GoreeCloud/tasks/actions/runs/38098549525
- **Unverified:** Full Todoist provider integration, source timezone user-profile handling, all-day/recurrence DST semantics, shared/geo feature migration, completed/archived snapshot freshness, actual persisted record-level parity, restoration, idempotency and Stable status. No live source import or production authority transfer.

## October 10 — one-shot Todoist import and source interval overflow guard

**Verified executable source revision:** `465f9a42be50b2b55e727b422a6c069bd9d2be57`.

- **UI repeat-write defense:** One consent/authorization callback can initiate at most one Todoist import attempt. After any failed or uncertain import response, the client discards the callback credentials and offers a fresh OAuth authorization link rather than allowing a second submission of the same code. In-place changes to the route authorization code now reinitialize callback validation.
- **Recurrence safety:** Unrepresentably large day/week repeat intervals are rejected by the pre-insertion source preflight; an integer overflow cannot silently produce a negative or incorrect destination interval.
- **Completed task fidelity:** Source completed-task project metadata, when provided, must agree with the completed task's project identity. Mismatches fail before importing.
- **Go importer and migration handler regressions: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38099169727
- **Frontend typecheck, focused Vitest and production build: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38099169701
- **Source Safety Baseline: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38099169770
- **Not proven:** The client guard is not server-side, durable, cross-session import idempotency; an upstream or server partial failure can still leave unknown destination state. Real Todoist API flows, complete source/destination readback, timezone-aware recurring deadlines, repeatable recovery, backup and rollback, release and Stable acceptance remain blocked. No live owner-data import or authority cutover occurred.

## October 10 — Today, sorting, pagination, and task-fetch recovery

**Last executable source revision:** `05f3f2f6855aaca408babe6acebf98dc3b8e9cb9` (the subsequent roadmap change is documentation-only).

- **Implemented:** Today focus route, main navigation and keyboard shortcut, reusable quick capture, and default overdue inclusion.
- **Implemented:** Overview/Today/Upcoming selectable sort orders (due date, priority, newest first) preserved in their route queries. Invalid sort parameters fall back to the existing due-date order.
- **Implemented:** Cross-project list pagination with filter-change reset; empty results no longer show an idle spinner; fetch failures offer an accessible retry affordance rather than claiming there are no tasks.
- **Frontend typecheck, existing targeted tests and production build: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38100071067
- **Source Safety Baseline: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38100071064
- **Go importer regression workflow: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38100071095
- **Pending:** The newly authored task-list sorting, pagination and error-recovery tests in `frontend/src/views/tasks/ShowTasks.test.ts` were not included in the existing targeted workflow command. They require a dedicated execution before being represented as passed; manual Glaze/accessibility, cross-browser and representative interaction acceptance also remain open.

This is source and automated-build evidence only. No Stable claim, production deployment or task-authority transfer.

## Multiline Quick Add duplicate-title follow-up

The hierarchy parser records the source `parentIndex`. Quick Add now uses `indexCreatableTasks` and `resolveBulkTaskRelations` instead of matching created tasks by duplicate-prone title strings. The resolver preserves input positions when blank titles were dropped and skips links when parent/child creation failed. The UI does not restore the entire batch after an uncertain bulk-write result and now warns about potentially created tasks and incomplete relationships.

- **Executable source revision:** `3118d171bce2ec5799ee4ca05cd02c8e182b2e6d`.
- **Typecheck, legacy focused tests, production frontend bundle: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38101020900
- **Source Safety Baseline: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38101021050
- **Go regression workflow: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38101020964
- **New helper scenarios:** isolated smoke checks passed for duplicate names, filtered entries, missing/invalid IDs; their Vitest file is committed but has **not** been executed by the current frontend workflow.
- **Still pending:** Dedicated run of `bulkTaskRelations.test.ts`, `parseSubtasksViaIndention.test.ts` and `ShowTasks.test.ts`; complete bulk failure-recovery/readback tests, accessibility and representative-device verification. Workflow expansion was blocked by tool safety checks. Do not claim comprehensive recovery or Stable.
- **Follow-up parser fix:** Mixed space/tab indentation now recognizes tab-prefixed children in the parser, with a new nested-tab regression on commit `9bb175d`. The new parser case has not yet run in the focused CI suite.

## October 10 — concurrent Quick Add and Today feature validation

**Validated feature source revision:** `e3462884635fb187f7e884063b0276a22fff6bf0`.

- **Quick Add duplicate-submit defense:** The submission lock activates synchronously before label/project preparation, avoiding a second concurrent bulk task creation before mutation loading begins. Capture errors are associated with the textarea and announced using `role="alert"`.
- **Today quick capture:** Tasks entered in Today default to a due date within the current day; an explicit parsed date takes precedence. Quick Add in other views retains its existing date defaults.
- **Bulk write fidelity:** Failed post-creation label/assignee operations are counted as incomplete details. Quick Add surfaces a warning without misrepresenting partially created tasks as absent or re-submitting all input.
- **Focused tests: PASS, 48/48 in five files at validated revision** on an isolated GoreeCloud Tasks branch checkout using the pinned pnpm dependencies and `vitest run`: `bulkTaskRelations.test.ts`, `parseSubtasksViaIndention.test.ts`, `ShowTasks.test.ts`, `task.test.ts` and `useQuickAddTask.test.ts`. A previously failing retry case was traced to a shallow test stub hiding the message's slot and corrected. This is real local execution, independent from CI.
- **Source Safety Baseline: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38101760759
- **Go regression workflow: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38101760675
- **Frontend Quality CI, including TypeScript and production build: PASS** — https://github.com/GoreeCloud/tasks/actions/runs/38101760662. A caught TypeScript mismatch in the new undated deadline fallback was corrected before this run.
- **Remaining gates:** The CI workflow still omits these five task-specific files from its targeted command. No runtime browser interaction acceptance, full backend/database recovery, accessibility conformance, backup/restore, production rollout or Stable qualification is demonstrated here.

## October 10, 2026 — task recovery and list continuity

**Exact validated executable source:** `b9cf57533b7841ed8544b6233632877f44677fcb`. This evidence does not qualify a production release.

- Quick Add preparation errors now have a valid English message. The caller preserves draft text before the bulk write begins.
- Bulk relation mapping refuses duplicate API task IDs, preventing ambiguous parent/subtask relationships.
- Relationship creation uses `runWritesSettled` to wait for every attempted independent relation write before reporting incomplete links; concurrent mode does not short-circuit after an early failure and serial mode continues after individual errors. Existing account-context fencing and uncertain-create warnings remain.
- Today Quick Add no longer forces a task-list remount. The bulk mutation already invalidates active task-list membership caches, preserving local list search and pagination.
- **Local focused Vitest: 67/67 passed across 8 task feature files** in a checkout of the exact source revision on the authorized laptop.
- **GitHub Frontend Quality: PASS** (TypeScript, identity/Tasks regressions, production frontend build): https://github.com/GoreeCloud/tasks/actions/runs/38106192714
- **GitHub Source Safety Baseline: PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38106192779
- **GitHub Todoist Import Integrity: PASS:** https://github.com/GoreeCloud/tasks/actions/runs/38106192715
- Remaining: representative browser/Glaze interaction and accessibility checks, backend/database post-write readback, full regression/security test suites, disaster recovery, deployment and Stable/authority qualification.

## October 10, 2026 — Quick Add recovery regression and first-project onboarding

**Validated executable candidate:** `2e1856d6301d2cdfded59b781ec59297550073fb` (draft development branch only).

- Quick Add tests cover label and assignee writes with one failed attachment and one successful attachment in the same batch, verifying the later write runs, only saved metadata appears in returned tasks, and incomplete details are reported. No uncertain batch creation replay.
- Today now links to `project.create` when project loading is complete and the account has no projects. New regression tests verify navigation and no loading-state flash, and maintain search/list identity after Quick Add.
- Exact-head [Frontend Quality](https://github.com/GoreeCloud/tasks/actions/runs/38107861211): **PASS**, includes Vue TypeScript checking, focused feature and identity regressions, and production frontend bundle.
- Exact-head [Source Safety Baseline](https://github.com/GoreeCloud/tasks/actions/runs/38107861209): **PASS**.
- Exact-head [Todoist Import Integrity Go guard](https://github.com/GoreeCloud/tasks/actions/runs/38107861157): **PASS**. Passing guard does not indicate a Todoist cutover.
- Isolated authorized-laptop Vitest: **11/11 passed** across `useQuickAddTask.test.ts` and `TodayTasks.test.ts`. Focused `pkg/models` Go tests for bulk creation, task relation create/delete and label create/delete: **PASS**. No production database or live user tasks were modified.
- Still pending: backend API persisted readback/recovery for partial metadata writes, browser/Glaze design and accessibility acceptance, full regression and threat-model coverage, rollback evidence and production/Stable authority gates.

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
