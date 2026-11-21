# SQLite online backup and recovery — development procedure

GoreeCloud Tasks runs SQLite with WAL. Copying a live database file alone may omit committed transactions still in the WAL. The first-party Python backup command uses sqlite3.Connection.backup for a consistent online snapshot and checks SQLite integrity and foreign-key consistency. It does **not** overwrite an existing output path. Successful verification is not a production disaster-recovery drill or encryption guarantee. A disposable, non-overwriting **restore-drill** command now reconstitutes a schema-v4 backup into a newly named file and verifies SQLite integrity, foreign keys, table counts and the changefeed cursor.

With the API Python environment installed on an authorized host:

    python -m goreecloud_tasks.backup verify --database /path/to/tasks.sqlite3
    python -m goreecloud_tasks.backup backup --database /path/to/tasks.sqlite3 --output /path/to/backup-unique.sqlite3
    python -m goreecloud_tasks.backup verify --database /path/to/backup-unique.sqlite3
    python -m goreecloud_tasks.backup restore-drill --backup /path/to/backup-unique.sqlite3 --output /path/to/new-test-restored.sqlite3
    python -m goreecloud_tasks.backup verify --database /path/to/new-test-restored.sqlite3

These are reference commands, not claims they ran against user task data. Choose unique private paths; never paste tokens, secrets, identifiable tasks or real internal endpoints into public logs. The backup file is created with owner-only file permissions (0600). Store off-host copies encrypted with access controls and a founder-approved retention policy.

**Recovery acceptance (manual, test-only):** Use a disposable test directory and a fresh isolated process. Run restore-drill against a snapshot and unique output path. This rejects a non-Tasks/v3-or-earlier schema, missing tables, corrupt or symlink sources, existing destinations and failed integrity/foreign-key verification. The drill compares counts of tasks, projects, change events, retry receipts, habits, checkins, plus highest feed cursor. Then optionally launch the API against the new test output and compare expected behavior. Do not use the drill to overwrite any live database. Do not replace a live DB or delete its WAL files without an approved maintenance and rollback plan. JSON export is not equivalent to a historical SQLite backup.

**Limitations:** No automated schedule, remote replication, encryption-at-rest, in-place/live restoration, host snapshot management, monitoring, production disaster-recovery drill or deployment. The disposable restore drill is verified only using synthetic fixtures. SQLite current schema version 4. Test and verify against the actual environment before relying on backups.

## Optional browser offline-vault backup (separate from the server database)

The web Offline workspace now offers explicit ciphertext-only download and passphrase-verified restore for a local encrypted vault, including unsent drafts. This cannot replace SQLite online backups: it does not capture the full server or guarantee another device's revisions. Restore requires the identical site origin and the original vault passphrase, refuses to overwrite an existing vault, and re-encrypts to a fresh vault identity. See ENCRYPTED OFFLINE recovery guidance in OFFLINE_WEB.md. No production backup/restore exercise or cross-origin migration has been certified.
