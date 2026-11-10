# Native bulk-edit operations — development evidence

**Scope:** GoreeCloud Tasks Linux GTK4 and Android Jetpack Compose. This change is on a draft PR, not a deployment, a stable release, a device migration or a new sync contract.

## Implemented

- Multi-select individual visible tasks or use **Select visible**. Selection is limited to 200 task IDs per batch. Changing the view, text search or priority/sort filter clears selections; Trash is not selectable.
- Apply **Complete**, **Reopen**, **P1–P4 priority**, **move to project/Inbox**, and **Move to Trash**. Trash requires an explicit confirmation and keeps individual task restoration.
- The Linux GTK4 interface wraps bulk controls in a FlowBox. Android Compose exposes a horizontally scrollable action row, native selection checkboxes, and an AlertDialog for batch Trash.
- Each action validates the complete list of unique IDs, supported action, and optional destination **inside a single SQLite transaction**. Missing task or project fails without changing any rows. A collision in durable local Trash rolls back the whole action.
- Repeating **Complete** does not overwrite an existing completion timestamp. Reopening clears completion metadata; Android also clears the imported exact-completion timestamp only when the completion state actually changes.
- No new third-party dependencies, network permissions, schema changes, or portable JSON backup fields. Existing independent browser/local SQLite stores remain separate.

## Verification

- Linux: `python3 -m unittest discover -s linux/tests -q`; `python3 -m py_compile linux/app.py linux/store.py`; `xvfb-run -a /usr/bin/python3 linux/tests/gui_smoke.py`. The GUI smoke uses a disposable XDG database, exercises selection and each action, and does not touch normal task data.
- Android: Robolectric `RestoreDatabaseTest` covers both successful batch operations and rollback on duplicate IDs, missing project/task, invalid actions, and a mid-batch Trash collision. Verify via GitHub Actions `gradle -p android :app:testDebugUnitTest :app:assembleDebug`, followed by APK identity and permission checks.
- Regression checks: browser `node --test web/*.test.mjs`, API `python3 -m unittest discover -s server/tests -q`, and `git diff --check`.

## Limitations and acceptance gates

- Android multi-select UI and screen-reader semantics require device-based manual QA, particularly at compact widths and large text sizes. GTK4 visual/focus/keyboard/assistive-tech acceptance also remains open.
- Selection is limited to the current rendered view. Changing a filter clears selected IDs; task IDs are revalidated transactionally at operation time.
- Recoverable Trash is device-local and intentionally excluded from the schema-1 portable JSON. Users must retain the original SQLite store (or verified SQLite snapshot) to preserve deleted tasks across device moves.
- A **batch action is not multi-device synchronization**. The browser continues to use a localStorage stale-tab guard, while native SQLite transactions do not create an online shared task registry.
- Subtasks, labels, rich descriptions, reminders, recurrence and secure sync remain future stages; none is implied by this update.
