# Experimental Tasks → DAV VTODO export contract

**Status: source-only, offline preview, November 10, 2026.** This is neither a deployed CalDAV connector nor automatic task sync, a real data migration, or a native client release.

## Purpose and verified compatibility context

GoreeCloud DAV's experimental [client integration reference](https://github.com/GoreeCloud/DAV/blob/feat/goreecloud-dav-foundation-20261105/docs/CLIENT-INTEGRATION.md) describes CalDAV VTODO. Its [independent-client synthetic test](https://github.com/GoreeCloud/DAV/blob/feat/goreecloud-dav-foundation-20261105/tests/VdirsyncerInteropTest.sh) exercises two-way VTODO through a DAV client, but has not exercised this Tasks serializer or real clients.

**GoreeCloud Tasks** implements `server/vtodo_export.py` with a pure `vtodo_preview(selected_live_task)` method. It produces a minimal RFC 5545 `text/calendar; charset=utf-8` VTODO bytestring with one task, never sends it and never writes a file.

The preview includes the stable `UID:urn:uuid:<task-id>`, `DTSTAMP` derived from the validated UTC updated timestamp, `SEQUENCE` from the task revision, `CLASS:PRIVATE`, completed status, a safely escaped task title as `SUMMARY`, and optional all-day `DUE;VALUE=DATE`. The output uses strict CRLF and 75-octet UTF-8-safe line folding; unpaired surrogates, Unicode directional overrides, control characters, deleted tasks and invalid dates fail closed.

Task metadata not specifically allowlisted (including private notes or account identifiers) is **not exported**. The preview intentionally omits recurrence, priority, alarms, participants, attachments, rich descriptions, foreign DAV properties and inverse import. It does not flatten or overwrite existing independent DAV entries.

## Future authorized integration gates

1. The user must explicitly choose which tasks and fields to share and preview the actual outgoing content. An internal serializer invocation does **not** constitute GoreeShield consent.
2. Enforce source actor/account and destination collection authorization through GoreeCloud Identity and Wardveil, with certificate-validated TLS and scoped credential storage. Never infer an authorization from a matching UUID.
3. Use ETag/conditional updates to avoid remote clobbering; define duplicate IDs, foreign properties, offline conflicts, tombstones, and retry semantics before permitting write-back.
4. Run disposable CalDAV interoperability and multi-account isolation checks with this serializer, then native-client and device acceptance, before advertising any integration.

**State distinction:** format adapter implemented in development source; pure tests are not end-to-end DAV interoperability, production release, or connectivity.

## Governing format

Conforms to the narrow VTODO properties, text escaping and line folding defined in [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). Source-level approximation and synthetic unit tests are not a formal conformance certification.
