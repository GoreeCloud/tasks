# Tasks architecture: verified baseline and intended boundaries

## Verified imported baseline

- Backend: Go task server, API, persistence, migration, authentication, and service modules inherited from Vikunja.
- Web UI: Vue + TypeScript/Vite, task editing, project navigation, list and board experiences, login, sharing, and settings inherited from Vikunja.
- Desktop: upstream desktop shell retained for compatibility; does not yet implement GoreeCloud-specific secure identity or packaging.
- Existing database migrations and API contracts are kept intact until tested migration paths are established.

## GoreeCloud-owned integration boundaries (planned unless verified)

| Boundary | Minimum next implementation | Status |
|---|---|---|
| Glaze | Stable tokens, components, keyboard/touch/contrast, responsive layouts, evidence | Partial token and identity integration only |
| GoreeCloud Identity | Verified session, tenant isolation, logout, migration, and auth policy | Not integrated |
| GoreeCloud Policy / Wardveil | Authorization audit, secure defaults, dependency and threat review | Not integrated |
| Privacy Shield | Data minimization, telemetry controls, consent, deletion and export | Not integrated |
| Everkeep | Encrypted backup/restore and tested disaster recovery | Not integrated |
| GoreeCloud Mesh | Scoped inter-service connectivity, failure modes, sync contracts | Not integrated |
| Observability | Privacy-preserving health checks, metrics, error redaction | Not integrated |
| Todoist migration | Account-limited export mapping, idempotent import, 100% reconciliation | Not integrated |

Do not mark planned services as active based on names, settings, CSS tokens, or diagrams. Preserve upstream interoperability until replacements have parity tests and reversible migrations.

## Security priorities

1. Audit authentication, authorization, sharing links, cross-tenant data boundaries, and admin operations.
2. Verify secrets and encryption defaults, CSRF/XSS and upload handling, audit logging, dependency SBOM and licensing.
3. Make remote telemetry and third-party service calls opt-in and documented, including any source inherited from upstream.
4. Introduce durable backups, restoration drills, and a failure/reconnect/sync conflict plan before real user data is migrated.
