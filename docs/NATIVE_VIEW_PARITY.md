# Native task view and filter parity — development evidence

**Status:** Source implementation on the draft Tasks feature branch. No changes to data storage, portable schema, accounts, synchronization, production release, or task migrations.

## User-facing changes

- **Linux GTK4:** Adds **Next 7 days** and **Overdue** to native view navigation, with an independent priority filter (All, P1–P4) and sort menu (Smart, Due date, Title).
- **Android Compose:** Adds **Next 7 days** and **Overdue** chips, priority-filter and sort controls (Smart, Due date, Title), with state retained while switching views during the current session.
- **Browser:** The existing feature branch already includes those date views, P1–P4 filtering, Smart/Due date/Newest/Title sorting and bulk actions.

## Shared date semantics

- **Today:** Tasks due today or earlier (includes overdue).
- **Overdue:** Open tasks due strictly before the current local date.
- **Next 7 days:** Open tasks due from today's date through six calendar dates later, inclusive. Uses calendar-day rather than elapsed-hour arithmetic so a daylight-saving transition does not change the range.
- **Upcoming:** Open tasks due strictly after today.
- Undated and completed tasks are excluded from the date-specific open views. Search and priority filters further reduce matching tasks.

## Implementation boundaries

Native filters are view-only: existing task data and order in SQLite remain unchanged. The browser still uses a localStorage snapshot; Linux and Android use independent SQLite databases. None is remotely synchronized. The Android domain object has no creation timestamp exposed to its UI, so **Newest-first sorting remains browser-only**; we have not fabricated timestamps or changed the schema solely to add that mode.

The native Trash screens deliberately ignore task priority/sort filters and preserve their recovery ordering. No additional permissions or third-party packages were introduced.

## Verification

- Linux: `python3 -m unittest discover -s linux/tests -q`, Python syntax compilation, and `xvfb-run -a /usr/bin/python3 linux/tests/gui_smoke.py`.
- Android: pure Kotlin regression tests in `TaskViewsTest.kt`; Android Gradle unit tests and debug APK verification passed in [run 41338368516](https://github.com/GoreeCloud/tasks/actions/runs/41338368516) for the view parity commit. The development laptop has no Gradle executable; newer changes require fresh CI.
- Browser regression suite continues to run in GitHub Actions. Native and browser accessibility, zoom and physical-device acceptance remain pending.

No Stable release assertion or Todoist migration is permitted from these changes alone.
