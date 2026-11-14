# Experimental Tasks → DAV VTODO export contract

**Status: source-only, offline preview, November 10, 2026.** This is neither a deployed CalDAV connector nor automatic task sync, a real data migration, or a native client release.

## Purpose and verified compatibility context

GoreeCloud DAV's experimental [client integration reference](https://github.com/GoreeCloud/DAV/blob/feat/goreecloud-dav-foundation-20261105/docs/CLIENT-INTEGRATION.md) describes CalDAV VTODO. Its [independent-client synthetic test](https://github.com/GoreeCloud/DAV/blob/feat/goreecloud-dav-foundation-20261105/tests/VdirsyncerInteropTest.sh) exercises two-way VTODO through a DAV client, but has not exercised this Tasks serializer or real clients.

**GoreeCloud Tasks** implements `server/vtodo_export.py` with a pure `vtodo_preview(selected_live_task)` method. It produces a minimal RFC 5545 `text/calendar; charset=utf-8` VTODO bytestring with one task, never sends it and never writes a file.

The preview includes the stable `UID:urn:uuid:<task-id>`, `DTSTAMP` derived from the validated UTC updated timestamp, `SEQUENCE` from the task revision, `CLASS:PRIVATE`, completed status, a safely escaped task title as `SUMMARY`, and optional all-day `DUE;VALUE=DATE`. The output uses strict CRLF and 75-octet UTF-8-safe line folding; unpaired surrogates, Unicode directional overrides, control characters, deleted tasks and invalid dates fail closed.

Task metadata not specifically allowlisted (including private notes or account identifiers) is **not exported**. The preview intentionally omits recurrence, priority, alarms, participants, attachments, rich descriptions, foreign DAV properties and inverse import. It does not flatten or overwrite existing independent DAV entries.

## Calendar import preflight — development only (November 11, 2026)

I require Tasks-to-Calendar transfers to fail closed rather than discard task semantics. `server/calendar_interop_preflight.py` implements a pure `calendar_import_preflight(selected_live_task)` diagnostic on top of the existing Tasks VTODO preview. It returns only fixed reason codes, profiles, and authorization warnings; it does **not** return task IDs, titles, notes, raw VTODO or a converted import and cannot grant consent or change storage.

For the source-reviewed, unmerged GoreeCloud Calendar VTODO parser at commit `bea6665b31b81fc9bf4310c3fc071b3c2ed519e6`, the diagnostic reports unsupported `SEQUENCE` and `CLASS:PRIVATE` in **every** Tasks preview; date-only `DUE` is an additional blocker. It also flags Tasks titles exceeding Calendar's 160-character limit, non-P3 priorities omitted by Tasks's VTODO export, unproven priorities, and the destination's failure to retain the source update timestamp. A report of `blocked` is expected, **not a defect in the guard**. Even removal of the two unsupported properties for a test must never be portrayed as preserving revisions or privacy classification.

Synthetic local tests exercise the diagnostic without user files or network. The separately pinned Calendar source-contract workflow tests the **actual** Calendar parser against the genuine Tasks serializer using disposable examples; it must fail if the source pin changes without review. An import, automated sync, migration or live Cross-Product Mesh connector is **not implemented**. Track actual interoperability under [Tasks issue #25](https://github.com/GoreeCloud/tasks/issues/25).

## Future authorized integration gates

1. The user must explicitly choose which tasks and fields to share and preview the actual outgoing content. An internal serializer invocation does **not** constitute GoreeShield consent.
2. Enforce source actor/account and destination collection authorization through GoreeCloud Identity and Wardveil, with certificate-validated TLS and scoped credential storage. Never infer an authorization from a matching UUID.
3. Use ETag/conditional updates to avoid remote clobbering; define duplicate IDs, foreign properties, offline conflicts, tombstones, and retry semantics before permitting write-back.
4. Run disposable CalDAV interoperability and multi-account isolation checks with this serializer, then native-client and device acceptance, before advertising any integration.

**State distinction:** format adapter implemented in development source; pure tests are not end-to-end DAV interoperability, production release, or connectivity.

## Governing format

Conforms to the narrow VTODO properties, text escaping and line folding defined in [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). Source-level approximation and synthetic unit tests are not a formal conformance certification.
