# GoreeCloud Tasks — isolated browser runtime acceptance

**Status:** Real Chromium/Firefox automated acceptance on the draft Tasks branch. This evidence covers synthetic task workflows and selected browser states; it is not a Stable release, a complete accessibility audit or an Android device test.

## Tested workflows and evidence

The first-party browser QA runner `qa/browser-acceptance.cjs` starts a local-only static server and uses independent browser contexts; no live GoreeCloud accounts, personal tasks, network APIs or production servers are involved.

- **Desktop (1366×900):** Fresh profile opens Light/Neutral despite a dark-preferring host setting; create, edit, bulk complete/reopen, recoverable Trash transfer/restore, theme change to Dark/Lagoon and persistence across reload. Keyboard `/` and `N` shortcuts work outside fields. Browser-local data remains after reload.
- **Backup drill:** Export a schema-1 JSON document with the synthetic active task, then import into a *different, empty browser profile* after explicit confirmation. The same task is restored. Local Trash is intentionally outside portable JSON.
- **Mobile (390×844):** Add task and change appearance from the native mobile settings menu; both browsers report no viewport horizontal overflow. The menu now closes when its appearance action is selected.
- **Effective zoom:** Applying CSS `zoom:200%` to the document root at a 390px mobile viewport yields about 195 CSS pixels of usable layout width; no horizontal overflow in either Chromium or Firefox after container/narrow-viewport corrections. This is **not** a substitute for human tests of actual browser toolbar zoom and OS font enlargement.
- **Accessibility:** Axe-core with WCAG 2 A/AA, 2.1 A/AA, 2.2 AA tags returns zero violations in the tested desktop and mobile states in each browser, with **two incomplete/manual-review items per scan**. Automation alone does not prove screen-reader or WCAG compliance. Chromium forced-colors mode was verified active, but the complete forced-color visual/composited contrast matrix remains untested.
- **Screenshots:** Browser QA produces full-page desktop, mobile and effective-zoom PNGs for both engines. The CI artifact is synthetic, temporary and retained for five days; screenshots are not stored in Git or authoritative Drive.

## Corrective UI changes

The full visible screenshots exposed a 10px effective-zoom horizontal overflow, dense 3-column mobile view navigation, cramped select/filter inputs, an unreadable compact header, and a successful action shown in error-red. The source fixes add narrow-layout fallbacks, clearer task selection vs. completion labels and 44px touch targets, an appropriately reflowed mobile header, and distinct semantic success/error feedback. The local browser tests were rerun after those changes.

## Reproduce

```sh
npm ci --prefix qa --ignore-scripts --no-audit --no-fund
./qa/node_modules/.bin/playwright install --with-deps chromium firefox
GC_TASKS_QA_DIR="$PWD/qa/evidence" node qa/browser-acceptance.cjs
```

The test-only dependencies are pinned to Playwright 1.64.1 and axe-core 4.10.3 with npm integrity hashes. Browsers are installed for QA only; **none of these packages is delivered to production Tasks clients**. The same commands run in the isolated GitHub Actions `browser-acceptance` job. PNGs are excluded from source control.

## Remaining acceptance

Human contrast and visual review of all themes/accents, true browser zoom and font scaling, RTL/localization, screen readers, accessibility focus and task edit dialogs at all sizes, native Android TalkBack/physical-device acceptance, Linux GTK Orca/focus checks, full recovery and production distribution remain outstanding. This work does not implement cross-device task synchronization, shared accounts, Todoist migration, subtasks, labels, reminders or recurring tasks.
