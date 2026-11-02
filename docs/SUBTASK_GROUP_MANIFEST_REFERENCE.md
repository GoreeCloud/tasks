# Schema-4 deletion-group manifest reference — isolated development

**Status:** Preview and adversarial test utilities only. None is called by the live browser, Android, GTK or sync services. Current clients must still reject schema-4 imports. This is not a migration or release.

## Proven failure mode

A record-only recovery group may be missing its grandchild. If all surviving rows' `groupSize` values are changed to match their reduced count, row-count checks alone can accept an incomplete subtree. Existing parent-chain validation does not reveal descendants that are simply absent. A full durable member manifest is needed for reliable crash/recovery validation.

## Independent manifest contract

`{groupId,groupRootId,deletedAt,memberIds}` stores sorted, unique task IDs expected in the group. The validator compares the independent expected member set against all present local Trash rows, checks root and timestamp metadata, validates membership ordering and disallows duplicates. It detects missing descendants even with forged per-row counts. JavaScript, Python and Kotlin reference implementations use the same field names and synthetic schema-4 fixture.

A manifest must eventually be stored **separately from Trash entries in the same transaction as the subtree deletion**, restored/deleted atomically with that subtree, and tested through database restart, rollback and disk corruption. The current reference functions merely compute/validate copies of in-memory data. They do not reserve IDs, write databases, enable hierarchy, or alter production imports.

## Limits and acceptance

This is an integrity check against partial/corrupted group membership, **not a cryptographic authentication mechanism**: a malicious actor who can rewrite both the independent manifest and Trash entries coherently can defeat it. A durable implementation may need a stronger checksum or authenticated record depending on the eventual threat model and device-key strategy. Do not claim tamper resistance or production recovery from the pure tests.

Before subtask UI is enabled, integrate with versioned schema-4 import, durable manifest persistence, native SQLite transaction fault injection, crash replay, separate original/Trash data integrity scans, cross-client recovery and manual TalkBack/Orca acceptance. The owner task registry remains Todoist until cutover sign-off.

## Disposable SQLite transaction exercise

`linux/subtasks_sqlite_reference.py` now adds a **namespaced `proposed_manifests` table** in an in-memory SQLite connection only. The subtree Trash transaction inserts the member manifest before moving task records, checks it against the finished Trash rows, and commits all together. Restore requires the independent record to match the full group, then removes the manifest in the same transaction as the row restoration. Tests inject SQLite faults after partial moves and verify rollback restores both the task/Trash state and the manifest. A deliberately deleted grandchild with adjusted remaining row counts is still rejected because the independent member list disagrees. The reference explicitly refuses any file-backed database and is not registered with native app storage, production import/export, or Android persistence.

Production integration must additionally validate manifest lifecycle across process restarts, protect against torn or tampered metadata, use signed/checksummed snapshots as appropriate, and define safe repair/escalation behavior. The reference proves an in-memory transaction property only.

**Cross-group dependency rule:** a previously trashed child group cannot be restored while its parent remains in a different deletion group. A synthetic reference test verifies that the attempted child restore leaves both manifests and all task records unchanged; restoring the parent's group first then permits the child's full recovery. This policy requires explicit user-facing recovery guidance before activation.

## Additional failure checks

The next acceptance tests must cover missing independent manifests and inconsistent persisted member metadata, and prove that any failed restoration leaves the proposed task, Trash and manifest tables unchanged. This is not a live schema-4 permission to write personal databases.

## Fail-closed corrupted/missing manifest tests

The in-memory SQLite reference now covers absent independent recovery metadata, changed root metadata, child groups restored before their trashed parent, and a simulated failure during manifest finalization after task restoration starts. Each failed operation leaves active, Trash, and manifest state unchanged; verified tests do not write personal SQLite databases. The recovery operator must not try to reconstruct a missing manifest from surviving Trash rows, because the full expected descendant set cannot be proven from those rows alone.

## Local payload digests

The pure reference now checks per-member SHA-256 of serialized task contents. This detects accidental content edits even if group IDs and counts match; it is not keyed authentication and is not portable across differing serializers.
