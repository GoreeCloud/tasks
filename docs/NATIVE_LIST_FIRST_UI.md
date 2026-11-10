# GoreeCloud Tasks — native list-first navigation increment

**Status:** Android Compose and GTK4/libadwaita source changes on draft PR #5. Screenshots supplied by the owner are design references, not assets or copied layouts. GC UI semantic colors, Light/Neutral first launch, and independent task data remain authoritative. Native-device visual/accessibility acceptance is not yet claimed.

## Android (Jetpack Compose)

- Material3 bottom navigation routes to **Today** and **Inbox**, focuses native **Search**, and opens a real **Browse** dialog for other views and local project destinations, including **Create project**.
- A native floating **Add task** action opens/closes the existing validated task composer, now scrollable independently of the list; saving closes it, while the task list is visible by default.
- Large promotional hero and permanent backup buttons no longer occupy the initial viewport. The app presents a compact current-view heading, open/completed counts, project-specific title, with private backup/restore and appearance controls available from **Settings**.
- Compact task rows retain independent accessible selection and completion checkboxes. **Edit task** and **Move to Trash** are in a context menu rather than permanently taking horizontal space. Existing confirmation, recovery and local SQLite transactions are unchanged.
- Navigation mapping is isolated in `TasksNavigation.kt` with JVM tests. No added Android permissions, dependencies, schema migrations or network access.

## Linux (GTK4/libadwaita)

- Native sidebar buttons route between **Inbox**, Today, Next 7 days, Upcoming, Priority, Completed and Trash. Direct project shortcuts include updated open-task counts, and the current view/project is highlighted with GC UI semantic foreground/container pairs.
- Main heading reflects the current view. Header **+ Add task** expands a native entry/priority/due-date form and collapses after saving; search, view, filters and task rows stay visible when capture is closed.
- An actual libadwaita breakpoint collapses the sidebar and the larger project/view selectors below 700px, providing **Browse** menu navigation for view/project selection while Search and list rows retain horizontal space. Settings groups appearance and private JSON backups. New-project controls, priority/sort filters and batch actions are collapsed until requested; **Ctrl+N** opens capture and **Ctrl+F** focuses Search. Completion is circular and independent bulk selection remains square, with semantic priority colors. Existing SQLite, Trash and XDG preferences retain their established behavior.
- The GTK smoke exercises real navigation, selected styling, reversible capture expansion, edit/Trash recovery and batch operations with disposable user data.

## Verification and limits

Local tests: `python3 -m unittest discover -s linux/tests -q`, `xvfb-run -a /usr/bin/python3 linux/tests/gui_smoke.py`, and two mapped-window GTK smoke runs (`gui_window_smoke.py 600` and `940`), plus browser Node/Playwright, API tests, Python compilation and whitespace checks. Android native compile, JVM tests, debug APK signature/permission checks are gated by GitHub Actions for the exact head commit; local Gradle is unavailable.

**Visual review completed on synthetic Linux preview only:** The first Xvfb capture was black because the application was registered without executing its GTK application event loop. Running the real app entry point with `GDK_BACKEND=x11` and Cairo rendering produced actual screenshots. I visually inspected Light/Neutral at desktop and compact native widths and Dark/Lagoon at desktop width. A 600×480 screenshot initially exposed clipping and an empty task viewport; the responsive Browse breakpoint and compact controls corrected it. The new mapped-window CI test verifies allocated widths/heights and visible task rows at **600×480 and 940×760**. Screenshots were kept local for temporary manual analysis, not copied into this repository or presented as new user-requested images.

**Still unverified:** Android physical-device touch/reflow/large-font/TalkBack for these changes; GTK Orca, real keyboard-only traversal, other distributions, large OS text scaling and high-contrast/forced-color combinations; owner visual acceptance; full recovery and release lifecycle. A visually reviewed synthetic screenshot and automated smoke do not constitute complete native accessibility certification. Remaining subtasks, sections, recurring reminders, labels, collaboration and voice features require separate versioned model/security work.

## First cross-client rich task metadata

Task descriptions are now supported in native Android and Linux capture/edit source and the browser. These are plain text, bounded to 2,000 UTF-16 code units, and use additive SQLite storage with a versioned portable schema 2 (schema 1 stays readable). See [schema-2 contract](PORTABLE_SCHEMA2_DESCRIPTIONS.md). This change does not implement subtasks, labels, reminders, or collaboration and does not authorize deployment.
