# GoreeCloud Tasks — Product Requirements & Acceptance Map

**Owner:** GoreeCloud founder
**Product:** GoreeCloud Tasks — Organize Everything. Accomplish More.
**Specification received:** October 31, 2026
**Status:** Product requirements approved for planning. Functional acceptance is **not** implied.
**Architecture authority:** [GoreeCloud Tasks Architecture](ARCHITECTURE.md)
**Design authority:** [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui)

## Purpose

A privacy-first, self-hostable, connected productivity experience for individuals, families, professionals, and teams. One coherent product, with native web, Linux and Android clients first. The long-term roadmap also includes Windows, macOS, iOS, wearables, and developer extension surfaces. Neither these platforms nor their capabilities are considered shipped merely by being listed here.

## Capability coverage

This mapping captures all 16 feature families in the founder's product specification. Detailed backlog planning belongs in tracked issues and evolving implementation documentation; the list below is product intent rather than verified implementation.

| # | Product area | Target behaviors | Delivery stage |
|---|---|---|---|
| 1 | Tasks and subtasks | Unlimited captures, Quick Add, natural-language/voice/email/document intake, rich descriptions and attachments, checklists and nested subtasks, dates, priority, reminders, assignees, comments, bulk actions, history, templates and sharing links. | A basic tasks; B richer models; D AI intake |
| 2 | Projects and organization | Inbox, personal/team projects, nested projects, sections, labels, favorites, four priorities, saved filters, project templates, archive/restore and progress. | A basic projects on web; B full personal; C team |
| 3 | Scheduling and calendars | Due vs deadline, time zone support, flexible recurring tasks, daily/three-day/weekly/monthly/agenda views, time blocking, conflict detection and external calendar overlays. | B; D calendar integrations |
| 4 | Views and discovery | Inbox, Today, Upcoming, Priority, Project, Label, Filters, Completed, Team and Productivity views, list/board/calendar layouts, sorting/grouping/drag-and-drop, AND/OR/NOT saved filters, full search. | A partial web; B personal; C/D advanced |
| 5 | Reminders and notifications | Time, recurring and location-triggered reminders; mobile/desktop/email/push alerts for tasks, assignments, comments, deadlines and mentions; per-device preferences and urgent alert controls. | B initial native local; C collaboration; D integrations |
| 6 | Collaboration and teams | Shared projects, invitations, task ownership, comments and mentions, activity, workspace roles, external guests, private projects, team directory, project ACLs and progress. | C |
| 7 | Productivity and analytics | Goals, streaks, points, achievements, vacation mode, completion trends, project health, risk forecasts, workload and team insights. | D |
| 8 | GoreeCloud AI | Conversational task operations, goal decomposition, title rewrites, priority/schedule recommendations, multilingual voice, document/PDF/image/handwriting extraction, email action items, natural-language filters and productivity insights. | D (all opt-in with explicit scopes) |
| 9 | Connected applications | Google/Outlook/Apple calendars and mail, CalDAV, Slack/Teams, Jira/Trello/Notion/OneNote, trackers, Zapier/Make/IFTTT/n8n, ChatGPT/Claude/Copilot/Gemini and MCP-compatible agents. | D, each provider independently gated |
| 10 | Workflow automations | No-code and natural-language builder, scheduled/event/manual triggers, task and messaging actions, templates, execution histories, retries, failures and repair. | D |
| 11 | Platforms and synchronization | Responsive browser experience; OS-native Linux/Windows/macOS/Android/iOS apps, widgets and share-sheet support, Wear OS/Apple Watch, offline storage and authenticated cross-device synchronization. | A first three; C sync; E additional OS |
| 12 | Import/export and recovery | CSV project/task imports, structured data/template exports, portable backups, verified restores, archives, account data deletion and lawful portability. | B personal; C server/teams |
| 13 | Developer platform | Secure versioned APIs, OAuth and scoped tokens, task/project/section/label/comment endpoints, webhooks, SDKs/CLI, MCP, integration and UI action extension points. | C secure foundation; D ecosystem |
| 14 | Personalization and accessibility | Light/dark/custom themes, GC UI tokens, project/label colors, sidebar/favorites, locale/time zone/week start/goal preferences, keyboard and assistive tech support, responsive accessible controls. | A initial; B comprehensive |
| 15 | Security and administration | Authentication, 2FA/recovery, private data, project/workspace roles and guests, sharing consent, encrypted transport/storage, revocation, audit, monitored backups and deletion controls. | C before public shared state |
| 16 | Advanced and future | Predictive scheduling/risk, AI project plans, conditional multi-step automations, conversation-linked work, enhanced integrations/analytics, expanded devices and collaborative presence. | E after stable core |

## Engineering acceptance boundaries

### Foundation (stage A)

**Implemented source targets:** native web shell, GTK4 desktop client and Android Compose client; first-party task models, local CRUD and priorities; initial projects and due-date operations in the web experience. Tests and build validations are separate acceptance checks and must be evidenced independently.

**Not yet accepted:** actual full-platform usability, complete native installer lifecycle, shared state, users and accounts, secure server, collaboration, automation, AI, notifications, calendar sync, stable product data import/recovery, official APK delivery.

### Personal experience (stage B)

Users can safely perform a full GTD-style personal workflow across native clients: capture, clarify, organize, schedule, review, complete, reopen, export and recover. Accessibility, offline safety, recurrence and time-zone correctness have tests. Avoid fake integration controls.

### Secure cloud and teams (stage C)

An independently reviewed self-hosted service enforces account/workspace authorization, reliable ordered synchronization, offline convergence, secure invitations, audit events and complete recovery. No shared data flows before those security tests pass.

### Intelligence and ecosystem (stage D)

Each AI and integration action requires explicit provider authorization, least privileges, observable results and consent to any source text sent to external models. AI suggestions must be previewable and reversible; automation executions are idempotent and auditable.

### Release expansion (stage E)

A platform is declared released/Stable only after its actual source, packaging, device/runtime, lifecycle, security, accessibility, data-loss recovery, update/rollback and distribution criteria are verified. Real native implementation is mandatory; a PWA or web-wrapper installer is not a native replacement.

## Migration rule

Todoist Free and any still-authoritative pre-migration GoreeCloud task registries remain authoritative until GoreeCloud Tasks has independently achieved Stable acceptance plus reconciliation, verified import/export and governance cutover. Do not import/delete customer or owner obligations as a byproduct of this development stage.

## Current tracked work

- [#1 — Secure sync service and shared contract](https://github.com/GoreeCloud/tasks/issues/1)
- [#2 — Linux and Android platform acceptance](https://github.com/GoreeCloud/tasks/issues/2)
- [#3 — Feature parity and personal productivity](https://github.com/GoreeCloud/tasks/issues/3)
- [#4 — Canonical repository inventory update](https://github.com/GoreeCloud/tasks/issues/4)
