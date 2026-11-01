# Portable backup compatibility fixture

`schema1-synthetic.json` is a **synthetic, non-sensitive** example of the
GoreeCloud Tasks portable schema-1 format. It contains no account, device or
production task data.

The same file is consumed by **all three** platform test suites:

- Browser/Node: `web/backup.test.mjs` validates exact JSON and export round trips
- Linux/Python: `linux/tests/test_backup.py` restores into an empty SQLite
  database, re-exports, and verifies task/project data and timestamp strings
- Android/Kotlin: `PortableRestoreTest` validates the same file, while
  `RestoreDatabaseTest` runs a Robolectric SQLite restore and re-export

`timestamp-contract.json` is the shared positive/negative timestamp validation matrix
used by the browser, Linux and Android tests. It refuses impossible calendar
days, 24:00, bad offsets, seconds/minutes outside 00–59, missing time zones,
overlong fractional seconds and timestamps unsupported by Android SQLite.
All three platforms must agree before a backup is considered portable.

The fixture covers multi-project assignments, an inbox task, Unicode titles,
a completed task, a future due date, ISO-8601 timestamps with microseconds,
explicit UTC and negative timezone offsets, and null completion metadata.

**Contract policy:** if one platform rejects the file or changes one of its
portable fields, CI fails. Do not weaken a validator merely to pass tests;
investigate the cross-platform contract and update the fixture/test together
only when a deliberate, versioned schema change is agreed. Nonportable private
settings, tokens and application state do not belong in this JSON format.

This is a format/regression fixture, not a real-world recovery warranty;
physical-device provider, storage failure and signed release acceptance still
require separate verification.

## Schema 2: plain-text descriptions

`schema2-synthetic.json` exercises an additive **plain-text description** field (up to 2,000 UTF-16 code units), including multiline Unicode notes and an empty description. Version 1 imports remain unchanged; exporters produce schema 1 when no active task has notes and schema 2 whenever notes must be preserved. Version 2 requires a `description` string on every task. Schema-1 input that attempts to add notes is rejected rather than silently discarding data. Trash remains device-local, not part of the portable export.
