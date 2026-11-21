# Security, privacy and operations boundaries

## Development threat model

- Task descriptions may contain private family notes and URLs; do not expose them in public logs, analytics or crash reports.
- The database is plaintext SQLite on the host. File/disk encryption, least privilege, backup encryption, multi-user access controls and verified restores are operator responsibilities until implemented and tested.
- A single shared token secures all tasks. It offers no per-user accountability, revocation of individual devices, roles, MFA, passkeys, OIDC or independent Identity integration.
- Web token remains in JS memory, not localStorage/cookies. Cross-site scripts, injected code and browser extensions in the trusted origin can still obtain secrets; enforce a strict content-security policy at deployment and restrict dependencies.
- Qt GUI reads token from environment. Android keeps the token in RAM; after disconnect a new token must be entered. TLS certificate validation remains the platform's default.
- Do not expose unencrypted HTTP beyond loopback, except emulator-specific Android debug test routing. Android release manifest disallows cleartext traffic.
- Front-end API messages are generic and must not display internal stack traces. No product telemetry is implemented, but the host, proxy, OS and Android runtime may produce unrelated logs.
- Concurrent edits use expected_version with SQLite BEGIN IMMEDIATE writer reservations; create/complete can use idempotent retry keys. Deleting a task redacts its previous change-event payloads and matching retry receipts. Backups and other clients may still retain copies; this is not full offline conflict resolution.

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
