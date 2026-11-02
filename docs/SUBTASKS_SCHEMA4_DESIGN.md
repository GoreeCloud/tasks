# Subtasks — proposed portable schema-4 engineering contract

**Status:** Design and threat-model review started after label-filter CI acceptance. **Not implemented**; do not treat this document as permission to migrate, deploy or enable subtask controls.

## Current constraints verified

Tasks currently persist as flat independent records. Browser portable backups support schemas 1–3; Linux stores data in task and deleted-task SQLite tables; Android uses SQLite v7. The browser stores active and Trash records in one local envelope. Existing operations support bulk priority/project changes, complete/reopen, duplicate, guarded deletion/restore and user-initiated backup/import. Todoist remains the authoritative registry until Stable acceptance and verified reconciliation.

The roadmap calls for real nested subtasks, not a textual checklist hidden in descriptions. Every implementation must preserve existing IDs, completed timestamps, labels, notes, project membership, offline capability and non-destructive restore.

## Recommended v4 wire model

Continue the existing flat `tasks` array, adding **required `parentId: string | null`** to every schema-4 task. A null parent is a root. A non-null parent references another task in the **same portable snapshot**, and must point to a task in the same project. Support a bounded depth of 3 levels initially (root plus two nested levels), with a maximum of 300 active tasks per project including descendants.

Reject in full, before writes: unknown/self parent IDs; cyclic relationships; depth overflow; cross-project parents; duplicate IDs; unsupported schema-4 field on schemas 1–3; parent/child data inconsistencies; and backups exceeding size/record limits. Treat a missing parent as a validation error, **never** silently convert an orphan into a root.

Legacy schemas 1–3 import as roots with null `parentId` in local storage; export schema 4 whenever any actual task has a parent. A schema-4 export includes explicit `parentId` for **all** tasks. Older clients must fail closed rather than discard parent relationships. API/sync must negotiate schema 4 separately; do not expose it to currently schema-1 outbox endpoints.

## Integrity and operation rules

- Create child: validate parent exists and project matches, generate a fresh ID, preserve ordinary validation. Children are full task records with their own notes, labels, priority, due date and completion history.
- Complete/reopen: affects the selected task only. Completing a parent with open descendants needs a visible warning or an explicit policy, never silent cascade.
- Move project: atomically move the parent **and descendants** or reject until the complete operation exists. Moving one child to a conflicting project is invalid.
- Delete to recoverable Trash: a parent and all active descendants must move as **one recoverable batch**. Previously trashed descendants retain their independent earlier recovery state; the parent/child links may be restored only when all prerequisites are present. Never leave active orphan records.
- Restore: validate the entire requested recoverable group, parent chain, IDs and project before a single transaction; collision or missing dependency rolls back all changes. Import remains empty-destination only.
- Duplicate: clearly choose either *duplicate parent only without children* or *duplicate subtree with new IDs and remapped references*. Recommend explicit **Duplicate subtree** as a distinct action so the existing Duplicate Task contract remains unsurprising.
- Bulk operations: confirm descendants are included or reject dangerous root-only project/Trash changes; never let hidden children be modified without a clear scope.
- Search, labels, priority and due-date views: preserve selected view constraints while showing enough parent context for matched children. Announce nesting and completion state to screen readers.

## Development sequence / acceptance

1. Implement pure schema-4 validators and one shared synthetic graph fixture with root, child, grandchild, completed task, labels, notes, exact timestamps, and negative cycle/orphan/mismatched-project cases.
2. Add read-safe, idempotent `parent_id` columns and guarded transactional operations to both native SQLite clients, keeping old 1–3 imports and recovery intact. Build full subtree Trash/restore safety before exposing deletion.
3. Add browser localStorage validation + mutation helpers with independent Trash recovery tests. Ensure existing three schema versions remain importable.
4. Add responsive hierarchical native GTK/Compose/browser UI with Add subtask, nested navigation, keyboard order, accessible disclosures, small-window and enlarged-font tests.
5. Run browser Node and Chromium/Firefox, Linux SQLite/GTK/Xvfb, Android JVM/Robolectric/debug APK CI, intentional malformed backup fuzz cases and cross-client recovery fixtures.
6. Require real Android/TalkBack, GTK Orca, human GC UI visual and owner data-recovery acceptance before merging. No automatic Todoist migration or production rollout.

## Explicit unresolved design decision

Choose and test the atomic Trash/restore group representation (e.g. device-local `deletion_group_id`) **before** writing schema-4 records. The current clients support independent Trash rows, not full parent subtree restoration. Until the grouped-recovery contract is implemented across all three clients, subtask storage and destructive actions should remain off by default.

## Preflight fixture and fail-closed evidence

The **proposed, unsupported** `fixtures/portable/schema4-proposed-synthetic.json` models a three-level parent chain using synthetic data. Browser, Linux and Android legacy import tests explicitly reject its schema number before modifying the target workspace. This is a safety guard **against silent hierarchy loss**, not evidence that subtasks work. The guard tests must be replaced with positive schema-4 import/export tests only after native/browser relationship validation and atomic group recovery are implemented.

## Read-only proposed v4 validators and recovery-model preflight

The next development increment includes **three independent, read-only graph validators**: `web/subtask-graph.mjs`, `linux/subtasks_contract.py`, and `android/.../SubtaskContract.kt`. Each validates the shared synthetic schema-4 fixture through its established schema-3 field/timestamp validation contract and then checks complete parent IDs, no cycles, max depth 3, same-project ancestry and at most 300 records per project (including Inbox). It leaves exact source timestamps and metadata intact. Its result is a **preview only**; none is registered with the live importer, Android SQLite helper, browser localStorage or GTK. Existing production schema-1–3 importers must still reject schema 4.

`web/subtask-trash-preview.mjs` is a separate **pure planning model**, not live task logic. It previews atomic deletion/restoration of a selected node and all active descendants, with a device-local deletion group ID, root ID and member count on each deleted record. Plans use copy-on-write state, validate graph integrity both before and after, and reject missing parents, conflicting IDs, incomplete groups, invalid timestamps and local Trash capacity overflow **before returning a candidate**. They never touch live storage or invoke user-visible destructive controls. In a later implementation, native clients need actual transaction boundaries and durable group metadata; complete rehydration and corrupted-group recovery must be proven before activation. This model is a specification tested with synthetic data, not a production recovery implementation.

## Native recovery planning parity (isolated, not shipped)

`linux/subtasks_recovery.py` and `android/.../SubtaskRecovery.kt` independently model the same pure grouped subtree Trash/restore algorithm as the browser prototype. All return copied candidate state, require graph validation before and after the operation, and reject incomplete groups, orphaned descendants, project inconsistency, active ID collisions, invalid deletion times and capacity overflow. Synthetic tests cover root and child branch deletion, full restoration and rollback without changing input state.

This is **not** a database migration or durable recovery implementation. The native models are intentionally unreferenced by live SQLite handlers. Production must add transactional storage, a verified durable group manifest and corruption detection. A member count alone catches accidental partial groups when metadata is intact, but cannot authenticate tampered metadata. Do not enable UI actions or schema-4 backup imports until these gates pass.
