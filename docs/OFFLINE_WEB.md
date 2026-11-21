# Encrypted offline web workspace — controlled development preview

GoreeCloud Tasks offers an **opt-in** encrypted offline draft vault in the web app's **Offline** view. It is **not a production multi-device offline-first engine** and does not replace the online API. No native offline queue exists yet.

## Encryption and trust boundary

- Non-extractable AES-256-GCM key derived in WebCrypto using PBKDF2-HMAC-SHA256 with 310,000 iterations, a random 16-byte per-vault salt, and a passphrase of at least 12 characters. A fresh 96-bit random GCM nonce protects every write.
- Additional authenticated data binds ciphertext to the browser origin. The only persistent record is the encrypted envelope in the IndexedDB database named goreecloud-tasks-offline-v1. This implementation never persists plaintext tasks/notes, API tokens, passphrases or encryption keys.
- Key and decrypted snapshot reside in memory only while the vault is unlocked. Lock, Disconnect and unmount clear the active session. Erase requires confirmation and deletes the local IndexedDB record, **not** server tasks or remote backups.
- An unlocked tab, hostile browser extension, keylogger, compromised web origin or weak passphrase can still compromise plaintext. This is at-rest encryption, not multi-factor authentication, a hardened key store, or protection against malicious running JavaScript.
- IndexedDB is per-origin and browser-profile, not bound to a verified GoreeCloud Identity subject. Use a trusted single-user browser and avoid concurrent tabs. Multi-tab coordination, per-user ACLs, key revocation and recovery remain unimplemented.
- Requires WebCrypto, HTTPS or localhost, and IndexedDB. First initialization requires a successful authenticated sync bootstrap. Each vault limits serialized data to 5,000,000 bytes, 5,000 tasks, 5,000 projects and 200 queued operations. Lost passphrases are unrecoverable and browsers may evict storage.

## Manual sync workflow

1. Log in with the development API token, which remains in memory. Open Offline, choose a passphrase and opt into encrypted storage. The client fetches a server bootstrap and saves an encrypted snapshot.
2. In an already-loaded browser tab, draft a standalone task with title/priority/optional due date/project, or queue a **title-only** edit for a cached task. The create draft receives a durable random idempotency key; the edit retains the original server expected_version.
3. Lock or close the tab. After reopening (when the app loads), unlock with the passphrase. Wrong passphrases or tampered ciphertext fail decryption.
4. When network access resumes, explicitly press **Sync now**. Create uses its original Idempotency-Key so an ambiguous network failure can be retried without duplicate task creation. Edit uses its original expected_version to prevent lost updates.
5. Each acknowledged write is removed from the encrypted queue. On HTTP 409, 404 or 410, sync **stops**, the conflicting operation is retained and marked CONFLICT; never silently overwrite server state. A network failure similarly preserves the queue. Inspect current online state and manually reconcile or discard conflicting drafts.
6. Once the queue is empty, the client refreshes a full bounded sync bootstrap. Refresh snapshot refuses to proceed while drafts remain. Vault deletion requires user confirmation.

## Unsupported / next acceptance gates

- Only web task create and title edit drafts are supported; completion/reopen, deleting tasks, subtasks, projects, habits, attachments, recurring changes, and provider migration remain online-only.
- No service worker or offline app shell: **the app must already be loaded** to draft offline. Closing the tab can prevent reopening until connectivity returns, even though the encrypted snapshot persists.
- This is not a fully tested changefeed replay/compaction engine; it uses new bootstrap snapshots. Native Android/Linux encrypted offline editing, Identity-scoped keys, Mesh transport, GoreeShield retention, Wardveil security controls, multi-tab write arbitration, background sync and production release/device acceptance remain pending.
- Cache erasure cannot delete unrelated devices, exports, backups or provider records. Use only with affirmative user consent and a trusted single-user browser. Do not interpret local synthetic tests as a real-world security audit.

## Synthetic cross-browser acceptance

Chromium, Firefox and WebKit acceptance fixtures check successful encrypted setup, ciphertext-only stored records, wrong-passphrase refusal, unlock/recovered queue, non-writing drafts, explicit replay, 409 conflict preservation without server overwrite, draft discard and local vault erasure. The test harness blocks all external browser requests.
