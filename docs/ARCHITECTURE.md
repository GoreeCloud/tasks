# Architecture — GoreeCloud Tasks 0.1 development preview

GoreeCloud Tasks is an original single-user, self-hosted API with three clients. The service uses Python/FastAPI, SQLite with WAL and foreign keys, UUID task IDs, a schema version and transaction-scoped writes. All authenticated routes live under `/api/v1`; no client needs an external SaaS account.

- **Web:** React/TypeScript/Vite; same-origin `/api` through the Vite loopback proxy in development, HTTPS reverse proxy required in production. Token held in tab memory, not persistent storage.
- **Linux:** genuine Qt Quick 6.12.0 (PySide6), QNetworkAccessManager, native window and controls; token from process environment; no Electron/Tauri wrapper.
- **Android:** Kotlin + Jetpack Compose host, actual Compose Multiplatform shared controls and GoreeCloud Material 3 Expressive theme from vendored, MIT-licensed `gc-ui` source. In-memory token. HTTPS normally; only Android debug emulator 10.0.2.2 permits local HTTP.
- **Database:** `projects(id,name,created_at,updated_at)`, `tasks(id,title,description,project_id,due_date,priority,tags,recurrence,series_id,completed_at,created_at,updated_at,version)`. Optimistic `expected_version` checks return HTTP 409 on conflict.
- **Recurrence:** completing a repeating task atomically saves completion and creates the next instance. Dates only; daily, weekly and monthly supported, no RRULE/due time or timezone.
- **Recovery:** JSON snapshot export is provided. For consistent SQLite+WAL backups, use SQLite's online backup API or pause writers; a raw copy of the active db file alone is insufficient.

**Current maturity:** clients require connectivity to the authoritative operator-controlled server and explicit refresh. Offline mutations/caching, sync cursor and tombstone log, local notifications, subtask hierarchy, identity/user ACLs, installation lifecycle and production deployments are NOT implemented. SQLite task list is capped at 1000 records; pagination remains backlog.

## Mandatory ecosystem boundaries

- GoreeCloud UI: implementation via a pinned copied-source adapter; design authority stays in `GoreeCloud/gc-ui`. Native device acceptance outstanding.
- GoreeCloud Identity: planned. The shared development token is NOT a multi-user Identity service.
- GoreeShield: privacy/consent/retention requirements; do not conflate with Wardveil.
- Wardveil: cybersecurity/threat detection/vulnerability/incident response requirements. Full controls unimplemented.
- GoreeCloud Mesh: future opt-in synchronization/events, not currently connected.

No third-party service data access or silent cross-product sharing is implemented. Future sync requires authenticated, authorized, privacy-governed event contracts, idempotency, deterministic conflicts and recoverability.
