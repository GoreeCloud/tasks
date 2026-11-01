# Browser productivity dashboard — development branch

**Scope:** GoreeCloud Tasks browser application. Native Linux, Android and experimental API are unchanged. This document tracks source changes on a feature branch; it is not a Stable release claim.

## Implemented source

- New **Overdue** and **Next 7 days** views with date-only calculations that cross daylight-saving changes correctly.
- Priority filter (P1–P4) and Smart / due date / newest / title sorting without mutating persisted task order.
- Selection of individual or all *visible* tasks. Bulk complete/reopen, set priority, move between projects/Inbox, and move to recoverable local Trash.
- Batch completion keeps existing completion timestamps when repeating an already-completed action. Every bulk edit validates targets before changing the local draft; persistence still uses the existing single-snapshot stale-tab check.
- Completion-rate dashboard metric; keyboard shortcuts **/** for search and **N** for new task; skip link and clearer selected-row states.
- Responsive GC UI semantic-token controls with visible focus, minimum touch targets, light/dark-mode backgrounds and forced-color fallbacks.

## Compatibility and safeguards

No new field is added to the task model or backup. The browser retains **schema 1** and existing Linux/Android portable JSON export/restore compatibility; the additional features operate on fields all clients already understand. Browser-local Trash remains outside exported JSON. Work is local-only: no multi-user accounts, device synchronization, remote notifications, cloud analytics or production deployment.

Bulk changes are *not* a database transaction across tabs; the existing localStorage stale-tab guard protects ordinary sequential edits, not simultaneous writer races. Bulk Trash still obeys existing limits and will fail without persisting partial changes when capacity/validation fails. Import remains a deliberate full active-workspace replacement.

## Verification

Run from repository root:

```sh
node --check web/app.mjs
node --test web/*.test.mjs
git diff --check
```

New regression coverage exercises date-boundary views, priority/sort combinations, all-or-nothing edits, stale IDs, completion history and portable backup round trips. Static UI contract tests verify required element IDs, uniqueness and shortcut controls.

**Pending for acceptance:** real browser interaction and keyboard/screen-reader checks, responsive zoom/RTL/contrast evaluation, comprehensive native client feature parity and Android physical-device acceptance. Initial browser and date-view parity passed CI in [run 41338368516](https://github.com/GoreeCloud/tasks/actions/runs/41338368516); additional native bulk actions require their own CI run. No release assertion follows from these tests. Avoid claiming release readiness based on source/test results alone.
