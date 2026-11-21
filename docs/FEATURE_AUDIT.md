# Competitor audit and phased feature roadmap

Research snapshot: 2026-11-20. Todoist and TickTick are proprietary, and no proprietary or AGPL competitor source has been copied.

| Capability | Benchmark | Current verified source status | Priority |
| --- | --- | --- | --- |
| Task/project CRUD | Both products | API, React and native Qt Quick/Compose CRUD source with project selection | Present development source |
| Due dates, priority, notes/labels | Both | API/web and native task editors with priority/tags/notes | P1 UX and device acceptance |
| Recurring tasks | Both | Date-only daily, weekdays, weekly, biweekly (14 days), monthly, yearly in API/React/Qt/Compose; simple previous-due-date step, no holidays, anchored RRULE, time zones or reminder engine | P1 richer scheduling/notifications |
| Today, Upcoming, search | Both | Web, Android and Linux view filters; API bounded search | P1 saved filters |
| Visual calendar, boards | Both | React month calendar and keyboard-accessible P1–P4 priority board with version-safe move buttons; drag-drop remains optional backlog | P1 |
| Native Linux and Android | Platform-specific | Expanded Qt Quick/Compose CRUD and filters; device/runtime acceptance pending | P1 |
| Offline editing and cloud sync | Both | Cursor feed, redacted tombstones, retry receipts plus opt-in encrypted web manual queue for standalone creates/title edits and bounded manual incremental changefeed pulls; an explicitly opt-in public-static-only app shell permits tokenless encrypted-vault reopen while disconnected; native full sync and background replay remain unimplemented | P1 |
| Notifications/reminders | Both | Not implemented | P1 |
| Subtasks/sections/checklists | Both | Versioned parent-child subtasks on API, React and native clients; sections and checklists pending | P2 |
| Habits | TickTick | Daily habit CRUD/check-ins/streaks in API and React; native Android/Linux create/list/check-in/undo/delete; offline sync and native advanced edit pending | P2 |
| Focus/Pomodoro | TickTick | Foreground-only web timer | P2 |
| Collaboration/sharing | Both | Not implemented; needs Identity/ACLs | P2 |
| Attachments, comments | Both | Not implemented | P2 |
| Import from Todoist/CSV, ICS/CalDAV | Interoperability | JSON/.ics VTODO export; generic CSV and limited Todoist project CSV preview/atomic import, with explicit date and unsupported-column warnings; TickTick/ICS import and CalDAV pending | P2 |
| Smart text entry, streaks, analytics | Varies | Not implemented | P3 |

**Component choices:** Original FastAPI + SQLite API and approved React, Qt Quick and Kotlin/Compose clients minimize coupling and licensing surprises. GoreeCloud UI MIT source is vendored and attributed. TaskChampion (MIT, https://github.com/GothenburgBitFactory/taskchampion) is a candidate for future sync evaluation, **not incorporated**. Vikunja (AGPL, https://github.com/go-vikunja/vikunja) is a competitor reference, **not incorporated**. RFC 5545 (https://www.rfc-editor.org/rfc/rfc5545.html) VTODO export is implemented; RRULE scheduling, import and CalDAV remain future work.

Research: https://todoist.com/features ; https://ticktick.com/about/features

**Acceptance gates:** backend tests, web production build, actual Android compile and device acceptance, Linux Qt Quick runtime, third-party license and security review, tested recovery, release signing and independent deployment verification. Do not label untested platform capability Stable.
