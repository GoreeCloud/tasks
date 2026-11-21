# Security, privacy and operations boundaries

## Development threat model

- Task descriptions, CSV imports and daily habit check-ins may contain private family information; do not expose them in public logs, analytics or crash reports. CSV preview validates input but never writes imported tasks; commit requires a matching checksum and unique idempotency key, with a bounded transactional import. Uploaded CSV contents must not be logged or retained outside the explicitly authorized task records. Habits have date-only history and privacy-preserving hard delete; there is no cross-device habit synchronization yet.
- The database is plaintext SQLite on the host. File/disk encryption, least privilege, backup encryption, multi-user access controls and **production** verified restores are operator responsibilities. New DB files use 0600 and new parent folders use 0700; existing files/directories are **not chmoded** and require a separate permissions audit. SQLite secure_delete is enabled per connection but cannot guarantee WAL, filesystem, backup or device erasure. The source includes a synthetic non-overwriting schema-v4 restore drill, **not** proof of live recovery readiness.
- A single shared token secures all tasks. It offers no per-user accountability, revocation of individual devices, roles, MFA, passkeys, OIDC or independent Identity integration.
- Opt-in web offline vault encrypts task snapshots and queued draft metadata at rest in IndexedDB using a passphrase-derived AES-GCM key; neither token nor passphrase is saved. Ciphertext-only vault backup export includes the origin and timestamp, but no token/key/passphrase/plaintext. Backup restoration validates the exact origin and passphrase, rejects tampered files and existing vaults, and re-encrypts under a fresh random salt before saving with atomic creation. An exported file can still be copied or attacked offline if the passphrase is weak, and backup deletion/retention remain operator-controlled. Offline protection does not prevent malicious browser extensions, XSS or unlocked-tab data theft; atomic revision-and-salt checks now reject stale writes across browser tabs, but do not supply multiuser isolation, automatic cross-tab merging, hardware key custody or complete client deletion propagation. Conflict review explicitly fetches the latest server task title/version; a rebase requires confirmation and only enqueues a new-idempotency-key edit for a later manual sync, which still checks the server's expected_version.
- Web token remains in JS memory, not localStorage/cookies. Cross-site scripts, injected code and browser extensions in the trusted origin can still obtain secrets; enforce a strict content-security policy at deployment and restrict dependencies.
- Qt GUI reads token from environment. Android keeps the token in RAM; after disconnect a new token must be entered. TLS certificate validation remains the platform's default.
- Do not expose unencrypted HTTP beyond loopback, except emulator-specific Android debug test routing. Android release manifest disallows cleartext traffic.
- API endpoints now apply defense-in-depth no-store/no-cache, nosniff, Referrer-Policy:no-referrer, X-Frame-Options:DENY, same-origin resource policy and a restrictive JSON CSP to 2xx/4xx responses. Pydantic request-validation errors are redacted across /api/v1 to prevent private rejected fields being echoed. Content-Length above 1 MiB is rejected with 413 on writes, but chunked-body caps, gateway rate limiting and any production network exposure remain unverified external requirements.
- Front-end API messages are generic and must not display internal stack traces. No product telemetry is implemented, but the host, proxy, OS and Android runtime may produce unrelated logs.
- Versioned subtasks require active parents and reject parent cycles; parent completion refuses unfinished descendants, and deleting a parent detaches children with change-feed upserts. Concurrent edits use expected_version with SQLite BEGIN IMMEDIATE writer reservations; create/complete/PATCH can use idempotent retry keys. Deleting a task redacts its previous change-event payloads and matching retry receipts. Backups and other clients may still retain copies; this is not full offline conflict resolution.

## Deployment gates

1. Choose a validated self-hosted node or Containers-managed workload, use a dedicated unprivileged account, restrict network and file permissions, run the included online backup/verify CLI, and independently rehearse a restore on an isolated test host.
2. Generate the secret in an external manager or environment; verify that API requests reject absent/wrong secrets. Rotate via controlled client reconnect.
3. Terminate HTTPS at a trusted gateway and apply network access control, request/body limits, rate limits, CSRF protections if adding cookie auth, and security headers.
4. Confirm an authenticated health/backup model without exposing private content on health endpoints.
5. Independently assess dependency versions, CVEs, license notices, build artifacts, mobile signing, update and rollback, Android device permissions, Linux runtime, accessibility and alerts.
6. No release or operational incident monitoring is configured by this source.

## GoreeCloud responsibilities

- **GoreeShield:** privacy, consent, retention, minimization and disclosures.
- **Wardveil:** vulnerabilities, threats, malware, intrusion response and security controls.
- **Identity:** authentication and authorization roadmap; current token is only a development boundary.
- **Mesh:** scoped interoperable synchronization; **not** enabled.
- **UI:** approved tokens/native patterns, not authentication or privacy controls.

## Vulnerability disclosure

For security issues, avoid filing public proof-of-concept exploit details or credentials. Use GitHub private vulnerability reporting if enabled, or a verified private channel with the repository maintainer. Do not store secrets in issues or repository code.
