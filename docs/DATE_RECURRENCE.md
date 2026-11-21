# GoreeCloud Tasks — date-only recurrence preview

**Authority:** GoreeCloud Tasks API schema v4, with corresponding React, Qt Quick 6.12 and Kotlin/Compose client forms. **Status:** development-source behavior; no time-zone-aware reminders or RRULE engine.

## Supported recurrence values

| API value | UI label | Next occurrence when completed |
| --- | --- | --- |
| none | Never | No successor |
| daily | Daily | Previous due date + 1 calendar day |
| weekdays | Weekdays | Next Monday–Friday after the previous due date; skips weekends, **not holidays** |
| weekly | Weekly | Previous due date + 7 calendar days |
| biweekly | Every 2 weeks | Previous due date + 14 calendar days, **not twice weekly** |
| monthly | Monthly | Previous due date + 1 calendar month, with end-of-month day clamped if needed |
| yearly | Yearly | Previous due date + 1 calendar year; a February 29 event advances to February 28 in a non-leap year |

Every repeating task **requires** a valid ISO YYYY-MM-DD due date. The server computes the next instance from the **previous instance's due date**, **not completion time**. It creates exactly one successor when a task is completed, including if its prior due date is already in the past. It does not automatically catch up to today or schedule an alarm. The completed instance and new active instance remain related by series_id; versioned completion and Idempotency-Key retries avoid duplicate successors.

Subsequent monthly/yearly dates are calculated using the immediately previous occurrence's stored date: January 31 → February 28 → March 28, not always the 31st. An anniversary originally due February 29 follows February 28 after a non-leap year. Preserve these simple, explicit rules until a separately planned anchored scheduler with RRULE/time-zone support is implemented and tested.

## Clients, API and import

The React composer/details form, Linux Qt Quick task composer/editor, Android Kotlin/Compose task editor, and authenticated API all accept the same canonical values. CSV generic-task import recognizes these cadence names; use biweekly in the recurrence column for the 14-day schedule. Unknown names, missing due dates and invalid date formats are rejected. Existing daily/weekly/monthly tasks preserve their previous meaning, and no database schema migration is necessary.

Portable JSON export stores recurrence names, but the .ics export produces individual private VTODO items, **not** an RRULE schedule or publicly reachable calendar feed. Importing into another calendar will not automatically reconstruct a recurring series.

## What is not implemented

This is not a complete recurrence or notification system: no user-adjustable repeat interval or week-of-month rule, holiday calendars, school/work schedules, reminder offsets, local times, time zones, daylight-saving handling, snooze, end-by date, RRULE parsing/emission, ICS import, CalDAV subscription, background Android alarms or push notifications. It does not integrate GoreeCloud Identity/notification delivery. Keep GoreeShield, Wardveil and Mesh gates separate.

## QA and recovery

Synthetic API acceptance tests cover Friday/Saturday/Sunday → Monday, Monday → Tuesday, 14-day interval, cross-year dates, leap-day clipping, exactly one generated successor under repeated Idempotency-Key, and expected-version conflicts. Native Qt tests verify accepted recurrence choices and due-date requirement. Actual Android compilation and genuine offscreen QML load must pass; physical device acceptance, production scheduling audit and signed packages remain pending.
