# GoreeCloud Tasks — native list-first navigation increment

**Status:** Android Compose and GTK4/libadwaita source changes on draft PR #5. Screenshots supplied by the owner are design references, not assets or copied layouts. GC UI semantic colors, Light/Neutral first launch, and independent task data remain authoritative. Native-device visual/accessibility acceptance is not yet claimed.

## Android (Jetpack Compose)

- Material3 bottom navigation routes to **Today** and **Inbox**, focuses native **Search**, and opens a real **Browse** dialog for other views and local project destinations, including **Create project**.
- A native floating **Add task** action opens/closes the existing validated task composer, now scrollable independently of the list; saving closes it, while the task list is visible by default.
- Large promotional hero and permanent backup buttons no longer occupy the initial viewport. The app presents a compact current-view heading, open/completed counts, project-specific title, with private backup/restore and appearance controls available from **Settings**.
- Compact task rows retain independent accessible selection and completion checkboxes. **Edit task** and **Move to Trash** are in a context menu rather than permanently taking horizontal space. Existing confirmation, recovery and local SQLite transactions are unchanged.
- Navigation mapping is isolated in `TasksNavigation.kt` with JVM tests. No added Android permissions, dependencies, schema migrations or network access.

## Linux (GTK4/libadwaita)

- Native sidebar buttons route between **Inbox**, Today, Next 7 days, Upcoming, Priority, Completed and Trash. The current view is highlighted using the selected GC UI palette's paired semantic container/foreground roles.
- Main heading reflects the current view. Header **+ Add task** expands a native entry/priority/due-date form and collapses after saving; search, view, filters and task rows stay visible when capture is closed.
- Project controls are stacked into smaller rows to improve narrower native window layouts. Existing per-task and batch editing, Trash restore, backups and XDG appearance preferences retain their established storage behavior.
- The GTK smoke exercises real navigation, selected styling, reversible capture expansion, edit/Trash recovery and batch operations with disposable user data.

## Verification and limits

Local tests: `python3 -m unittest discover -s linux/tests -q`, `xvfb-run -a /usr/bin/python3 linux/tests/gui_smoke.py`, browser Node/Playwright, API tests, Python compilation and git whitespace checks. Android native compile, JVM tests, debug APK signature/permission checks are gated by GitHub Actions for the exact head commit; local Gradle is unavailable.

**Still unverified:** Android physical-device touch/reflow/large-font/TalkBack for these changes; GTK full rendered screenshot, Orca/keyboard/focus and varying distro/scale QA; user-verified visual similarity across accents/modes; backups and full release lifecycle. A basic Xvfb root capture was black without a window compositor, so no screenshot visual acceptance is inferred from it. Remaining subtasks, sections, recurring reminders, labels, collaboration and voice features require separate versioned model/security work.
