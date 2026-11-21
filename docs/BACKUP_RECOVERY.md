# SQLite online backup and recovery — development procedure

GoreeCloud Tasks runs SQLite with WAL. Copying a live database file alone may omit committed transactions still in the WAL. The first-party Python backup command uses sqlite3.Connection.backup for a consistent online snapshot and checks SQLite integrity and foreign-key consistency. It does **not** overwrite an existing output path. Successful verification is not a production disaster-recovery drill or encryption guarantee.

With the API Python environment installed on an authorized host:

    python -m goreecloud_tasks.backup verify --database /path/to/tasks.sqlite3
    python -m goreecloud_tasks.backup backup --database /path/to/tasks.sqlite3 --output /path/to/backup-unique.sqlite3
    python -m goreecloud_tasks.backup verify --database /path/to/backup-unique.sqlite3

These are reference commands, not claims they ran against user task data. Choose unique private paths; never paste tokens, secrets, identifiable tasks or real internal endpoints into public logs. The backup file is created with owner-only file permissions (0600). Store off-host copies encrypted with access controls and a founder-approved retention policy.

**Recovery acceptance (manual, test-only):** Use a disposable test directory and a fresh isolated process. Verify a backup, place it under a new test filename, launch the API against that copy, and compare expected task/project counts and API behavior. Do not replace a live DB or delete its WAL files without an approved maintenance and rollback plan. JSON export is not equivalent to a historical SQLite backup.

**Limitations:** No automated schedule, remote replication, encryption-at-rest, full restore CLI, host snapshot management, monitoring, disaster-recovery drill or production deployment. SQLite current schema version 4. Test and verify against the actual environment before relying on backups.
