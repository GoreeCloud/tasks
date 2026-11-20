# Competitor audit and phased feature roadmap

Research snapshot: 2026-11-20. Todoist and TickTick are proprietary, and no proprietary or AGPL competitor source has been copied.

| Capability | Benchmark | Current verified source status | Priority |
| --- | --- | --- | --- |
| Task/project CRUD | Both products | API + React; native read/create/complete | Present |
| Due dates, priority, notes/labels | Both | API/web; native subset | P1 parity |
| Recurring tasks | Both | Simple daily/weekly/monthly | P1 RRULE/timezones |
| Today, Upcoming, search | Both | Web lists/search; API filters | P1 richer filters |
| Visual calendar, boards | Both | Not implemented | P1 |
| Native Linux and Android | Platform-specific | Qt Quick/Compose source | P1 runtime acceptance |
| Offline editing and cloud sync | Both | Not implemented; only conflict-safe server writes | P1 |
| Notifications/reminders | Both | Not implemented | P1 |
| Subtasks/sections/checklists | Both | Not implemented | P2 |
| Habits | TickTick | Not implemented | P2 |
| Focus/Pomodoro | TickTick | Foreground-only web timer | P2 |
| Collaboration/sharing | Both | Not implemented; needs Identity/ACLs | P2 |
| Attachments, comments | Both | Not implemented | P2 |
| Import from Todoist/CSV, ICS/CalDAV | Interoperability | JSON export only | P2 |
| Smart text entry, streaks, analytics | Varies | Not implemented | P3 |

**Component choices:** Original FastAPI + SQLite API and approved React, Qt Quick and Kotlin/Compose clients minimize coupling and licensing surprises. GoreeCloud UI MIT source is vendored and attributed. TaskChampion (MIT, https://github.com/GothenburgBitFactory/taskchampion) is a candidate for future sync evaluation, **not incorporated**. Vikunja (AGPL, https://github.com/go-vikunja/vikunja) is a competitor reference, **not incorporated**. RFC 5545 (https://www.rfc-editor.org/rfc/rfc5545.html) is a future recurrence/ICS standard, not implemented.

Research: https://todoist.com/features ; https://ticktick.com/about/features

**Acceptance gates:** backend tests, web production build, actual Android compile and device acceptance, Linux Qt Quick runtime, third-party license and security review, tested recovery, release signing and independent deployment verification. Do not label untested platform capability Stable.
