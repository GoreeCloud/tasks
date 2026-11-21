# GoreeCloud Tasks — private iCalendar export (development preview)

The self-hosted API now supports an **authenticated, on-demand read-only iCalendar VTODO file** for basic interoperability with clients that support RFC 5545 task components.

- **Endpoint:** GET /api/v1/export.ics (requires the same single-user bearer token as all Tasks data routes).
- **Web:** Explicit "Export calendar" button downloads goreecloud-tasks.ics. No automatically published calendar subscription endpoint, external requests, tracking, or task data sharing are enabled.
- **Content:** VCALENDAR containing one VTODO per recorded task, including unique task UID, UTC DTSTAMP, private CLASS, escaped SUMMARY and DESCRIPTION, date-only DUE, completed status and timestamp, priority and tags. Current tasks are recorded as independent instances, including successors of recurring tasks.
- **Privacy:** Response carries Cache-Control: no-store, download Content-Disposition and nosniff. Calendar files contain task names and notes in plaintext; use encrypted storage, private transfers and delete unwanted downloaded copies. Possessing a copied file gives access to its content irrespective of later server changes.
- **Bounds:** Limited to 5,000 task records per request to prevent unbounded export memory use. Explicit HTTP 413 above this limit.

The serializer escapes RFC 5545 TEXT metacharacters, strips control-character injection, emits CRLF line boundaries and folds physical lines to at most 75 UTF-8 bytes without splitting code points. Source backed by the standard https://www.rfc-editor.org/rfc/rfc5545.html . Its tests include escaped comma/newline/semicolon and arbitrary Unicode with line folding, as well as authentication and secure response headers.

**Not implemented:** iCalendar import, CalDAV server, calendar sharing, event subscriptions, RFC 5545 RRULE-based recurring task expansion, due times and timezones, native OS calendar permissions, invitations, delegated access, reminders or scheduling daemon. Applications that support only VEVENT and not VTODO may not display exported tasks; do not represent this file as a general calendar-event export.

No user data, live account, existing Vikunja service, or production calendar feed has been read or modified in validation. Tests use temporary synthetic task fixtures.
