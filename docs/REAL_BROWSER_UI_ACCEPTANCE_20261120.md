# GoreeCloud Tasks — real-browser source acceptance (2026-11-20)

**Source scope:** Public `GoreeCloud/tasks` development `main` base `c1666cc6bd8ca8573140b3681e09f6b8908fd9ec` plus this isolated review branch. Existing first-party GoreeCloud UI alpha snapshots are retained at their verified, attributed source pin `42965f8682c22973b4247d58238e68aa63d86523` (see `vendor/gc-ui/PROVENANCE.md`). No new brand colors, dependencies, auth system, user data, migration or native-app code was introduced.

## Actual observed defect and correction

The source React workspace previously expanded to **807 CSS px** inside a **390 CSS px** dark Chromium viewport after a synthetic sign-in. DOM geometry isolated the mobile sidebar/nav's *automatic min-content width* as the cause: the horizontal navigation's natural width forced the one-column app grid and main content to 807px even though the nav itself had `overflow-x:auto`. The resulting page overflow affected task composer, list and focus views. The correction keeps the nav horizontally scrollable **within** the intended viewport using `minmax(0,1fr)` on the compact workspace grid, `min-width:0` on its sidebar, and explicit `min-width:0; max-width:100%` on the scrolling nav. At 390px and 320px, the actual document now reports exactly the viewport width; it does not hide the excess navigation by clipping the entire page.

A fresh checkout also incorrectly reported `android/gradlew.bat` as modified because Git's `*.bat text eol=crlf` attributes attempted to renormalize an already-CRLF Git blob. The staged change stores the wrapper with standard LF in the **Git index** while preserving **82 CRLF lines on Windows-compatible working-tree checkout**; the executable logic is unchanged. Verified worktree bytes normalize exactly to staged blob bytes. This is a reproducible-source hygiene fix, not Android runtime validation.

## Source-controlled, opt-in genuine browser QA

`web/tests/browser-acceptance.mjs` is an isolated Playwright Core runner that opens the actual React/Vite app from `http://127.0.0.1:18756`. It intercepts *every* `/api/v1/` request with a stateful in-memory response fixture, requires an obviously synthetic 32+ character login token, and **blocks non-loopback traffic**. Neither fake task data nor fake credentials can reach a real Tasks backend, and the script never installs software, changes OS accessibility settings, or invokes an actual cloud integration. Each scenario exercises native form submit; project/task fetch; create, edit, query filter, versioned complete and completed-view navigation; focus timer start/pause; accessible selectors, mobile document reflow and absence of uncaught JS/runtime/network errors.

Executed locally on **real browser engines** with the following verified version labels:

| Browser engine | Desktop 900×800 light | Mobile 390×844 dark | Compact 320×760 light |
| --- | --- | --- | --- |
| Chromium 159.0.8154.6 | PASS | PASS | PASS |
| Firefox 159.0 | PASS | PASS | PASS |
| Linux WebKit 27.2 | PASS | PASS | PASS |

**9/9 end-to-end browser workflow scenarios PASS.** The OS dark semantic role reports `#BFB8FF` in the dark Iris viewport and light `#5146C8` in the light cases. Reported page widths equal viewports after the fix. A separate `npm test` contract suite (**3/3 PASS**) verifies that a missing browser binary fails closed and guards the source layout, semantic imports and synthetic mock-only behavior. Locked `npm ci --ignore-scripts`, TypeScript check and Vite production build: **PASS**. The source workflow executes the three Node tests on every protected web-build CI job; actual browser engines remain opt-in and require explicit pinned local binary paths.

### Reproduce without a real account

1. From `web/`: `npm ci --ignore-scripts`, then `npm run dev -- --port 18756 --strictPort`. This local dev server must bind to `127.0.0.1`.
2. In a second shell from `web/`, set `GC_PLAYWRIGHT_CORE_MODULE` to an **absolute inspected file** path of Playwright Core's `index.mjs`, and `GC_CHROMIUM_BIN`, `GC_FIREFOX_BIN`, `GC_WEBKIT_BIN` to existing, inspected executable paths. Run `npm run browser:acceptance`. The test refuses missing paths and never downloads browsers.
3. Optionally set `GC_QA_SCREENSHOTS_DIR` to an **existing absolute directory** to capture only synthetic task/focus states. Do not point it at private user folders. Delete artifacts when no longer needed.

### Screenshots visually inspected

- [Dark mobile 390px — synthetic task list](evidence/tasks-chromium-mobile-dark-tasklist.png)
- [Light desktop 900px — synthetic task list](evidence/tasks-webkit-desktop-light-tasklist.png)
- [Light compact 320px — focus timer](evidence/tasks-chromium-compact-light-focus.png)

These are rendered development UI screenshots, not illustrations of a deployed product or real user content. The deliberate horizontal tab-scrolling navigation is not a substitute for keyboard or human mobile accessibility acceptance.

## Still open

Real token-backed tasks API/SQLite end-to-end with a separate ephemeral test database; actual physical Android Compose and Qt Quick Linux app interaction; human TalkBack, Orca, VoiceOver/NVDA spoken inspection; official Safari on Apple hardware; genuine 200–400% browser zoom, RTL and long translations; authentication failure/recovery, accessibility under large data sets, backend sync/security/privacy and backup/restore; founder visual acceptance; and any Stable/Anchor release designation. **No Stable release, signed APK, live deployment or product-wide completion is implied by a green CI job or synthetic browser test.** Source-owned acceptance evidence supplements, but does not replace, the canonical GoreeCloud Drive governance.

Rollback: revert the protected PR to restore former CSS and test scripts. The wrapper source bytes change only in Git normalization. No migration, external service or stored data was touched.
