# Android schema-4 subtree recovery — transaction acceptance gates

**Status: pre-implementation review only.** Hierarchical subtasks and schema-4 imports remain disabled. This document does not authorize migration of `TasksDatabase`, installation, or release.

## Verified dependencies

The proposed Kotlin `SubtaskRecovery` planner creates and restores grouped Trash records. `SubtaskGroupManifest` validates the independent expected member list, group metadata and per-task SHA-256 digests. These are pure previews, not durable Android storage. Linux has a separate in-memory SQLite transaction reference with rollback fault tests; it is not a guarantee of Android SQLite behavior.

## Required Android parity exercise

Use a fresh Robolectric-created **in-memory** `SQLiteDatabase` only, with explicitly namespaced proposed active, Trash and manifest tables; reject any file-backed database. No code should call the live `TasksDatabase` helper, touch persistent user records, modify permissions or accept schema-4 backups in production.

For deletion, compute the validated subtree plan, capture an independent group manifest and perform the manifest insertion plus all active-to-Trash moves inside **one** SQLite transaction. Verify the final Trash set against the manifest before committing. On failure, active, Trash and manifest must all remain unchanged.

For restoration, independently read and validate the persisted manifest, verify every Trash member and content digest, validate the parent/project graph and ID collisions, then move all rows to active and remove the manifest inside **one** transaction. A missing or corrupt manifest must fail closed, not be reconstructed from surviving rows.

## Mandatory regression matrix

- Full root–child–grandchild move and restore retains IDs, Unicode descriptions, labels and exact completion timestamps.
- Child subtree deleted in a different group cannot restore while its parent remains deleted; restore parent first, then child.
- Injection after manifest insertion, after the first moved child, and during manifest cleanup rolls back all proposed tables.
- Missing grandchild with forged remaining group counts fails independently of row count.
- Modified task notes with unchanged ID/group metadata fails content-digest comparison.
- Missing, duplicated, reordered, mismatched or corrupt manifests reject restoration before any write.
- Duplicate group IDs, unknown parent, self-parent, cycle, cross-project parent and depth overflow cannot modify data.
- A second in-memory SQLite snapshot preserves the independent manifest and restores without affecting its source.
- App process restart, disk crash and physical-device recovery remain separate future gates; in-memory tests do not satisfy them.

No user-facing Add subtask, nested Delete, or recovery buttons should be enabled until durable on-device implementation, real assistive technology verification, full cross-client backup coverage and owner acceptance are complete.

## Local-only manifest compatibility boundary

The current schema-1/2/3 portable backups intentionally exclude recoverable Trash. The proposed schema-4 format must continue to exclude device-local deletion groups, Trash rows and independent manifests unless a *separate*, reviewed versioned recovery format is created. A normal schema-4 import must validate the parent graph, not import foreign recovery state.

The existing digest references hash locally serialized JSON. JavaScript `JSON.stringify`, Python `json.dumps(sort_keys=True)`, and Android `JSONObject.toString()` need not produce identical byte sequences for semantically identical task objects. **Never compare these hashes across devices or silently reinterpret an imported remote digest as locally verified.** Create a new independent manifest only when the destination itself performs a validated subtree move to local Trash, in the same transaction as those moved records.

If future cross-device Trash recovery is requested, design an explicit canonical encoding and independent integrity/authentication and conflict-resolution contract, with common byte-level test vectors, before enabling it. Local SHA-256 remains an accidental-corruption check, not a keyed proof of authenticity. A mismatched manifest must block recovery rather than trigger automatic reconstruction from the possibly incomplete Trash rows.
