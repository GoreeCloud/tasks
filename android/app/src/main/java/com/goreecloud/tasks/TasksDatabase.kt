package com.goreecloud.tasks

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.util.UUID

internal data class TaskRecord(
    val id: String,
    val title: String,
    val priority: Int,
    val completed: Boolean,
    val dueDate: String?,
    val projectId: String?,
    val description: String = ""
)

internal data class ProjectRecord(val id: String, val name: String)

/**
 * On-device private SQLite database. No Internet permission or server sync.
 *
 * V2 adds projects/dates, V3 completion timestamps, V4 exact imported timestamps,
 * V5 adds durable device-local Trash, V6 task descriptions in both tables.
 * All upgrades preserve existing task rows.
 */
internal class TasksDatabase(context: Context) :
    SQLiteOpenHelper(context, "goreecloud-tasks.db", null, 6) {

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        db.setForeignKeyConstraintsEnabled(true)
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        db.execSQL(
            "CREATE TABLE tasks (" +
                "id TEXT PRIMARY KEY, title TEXT NOT NULL, " +
                "priority INTEGER NOT NULL DEFAULT 4 CHECK(priority BETWEEN 1 AND 4), " +
                "completed INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, completed_at INTEGER, created_at_exact TEXT, completed_at_exact TEXT, " +
                "due_date TEXT, project_id TEXT REFERENCES projects(id) ON DELETE SET NULL, " +
                "description TEXT NOT NULL DEFAULT '')"
        )
        db.execSQL("CREATE INDEX idx_tasks_priority ON tasks(completed, priority, created_at)")
        db.execSQL("CREATE INDEX idx_tasks_due_date ON tasks(completed, due_date)")
        createTrashSchema(db)
    }

    private fun createTrashSchema(db: SQLiteDatabase) {
        // Intentionally no FK: deleted records retain original project links.
        db.execSQL(
            "CREATE TABLE IF NOT EXISTS deleted_tasks (" +
                "id TEXT PRIMARY KEY, title TEXT NOT NULL, priority INTEGER NOT NULL, " +
                "completed INTEGER NOT NULL, created_at INTEGER NOT NULL, " +
                "completed_at INTEGER, created_at_exact TEXT, completed_at_exact TEXT, " +
                "due_date TEXT, project_id TEXT, deleted_at INTEGER NOT NULL, " +
                "description TEXT NOT NULL DEFAULT '')"
        )
        db.execSQL("CREATE INDEX IF NOT EXISTS idx_deleted_tasks_when " +
            "ON deleted_tasks(deleted_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            db.execSQL("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
            db.execSQL("ALTER TABLE tasks ADD COLUMN due_date TEXT")
            db.execSQL("ALTER TABLE tasks ADD COLUMN project_id TEXT REFERENCES projects(id) ON DELETE SET NULL")
            db.execSQL("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(completed, due_date)")
        }
        if (oldVersion < 3) {
            // Preserve historical completions without fabricating a completion date.
            // Earlier records can have completed=1 and completed_at=NULL.
            db.execSQL("ALTER TABLE tasks ADD COLUMN completed_at INTEGER")
        }
        if (oldVersion < 4) {
            // Preserve sub-millisecond timestamps from portable Linux backups
            // without changing the existing INTEGER columns or task ordering.
            db.execSQL("ALTER TABLE tasks ADD COLUMN created_at_exact TEXT")
            db.execSQL("ALTER TABLE tasks ADD COLUMN completed_at_exact TEXT")
        }
        if (oldVersion < 5) createTrashSchema(db)
        if (oldVersion < 6) {
            // Upgrades from versions 1–4 create the Trash table above using
            // the current schema. Avoid a duplicate-column ALTER in that case.
            for (table in listOf("tasks", "deleted_tasks")) {
                val existing = mutableSetOf<String>()
                db.rawQuery("PRAGMA table_info($table)", null).use { cursor ->
                    while (cursor.moveToNext()) existing.add(cursor.getString(1))
                }
                if ("description" !in existing) {
                    db.execSQL("ALTER TABLE $table ADD COLUMN description TEXT NOT NULL DEFAULT ''")
                }
            }
        }
    }

    fun listTasks(): List<TaskRecord> {
        val records = mutableListOf<TaskRecord>()
        readableDatabase.rawQuery(
            "SELECT id,title,priority,completed,due_date,project_id,description FROM tasks " +
                "ORDER BY completed,priority,CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,due_date,created_at DESC",
            null
        ).use { cursor ->
            while (cursor.moveToNext()) {
                records += TaskRecord(
                    cursor.getString(0),
                    cursor.getString(1),
                    cursor.getInt(2),
                    cursor.getInt(3) == 1,
                    if (cursor.isNull(4)) null else cursor.getString(4),
                    if (cursor.isNull(5)) null else cursor.getString(5),
                    cursor.getString(6)
                )
            }
        }
        return records
    }

    fun listDeletedTasks(): List<TaskRecord> {
        val records = mutableListOf<TaskRecord>()
        readableDatabase.rawQuery(
            "SELECT id,title,priority,completed,due_date,project_id,description FROM deleted_tasks " +
                "ORDER BY deleted_at DESC,id", null
        ).use { cursor ->
            while (cursor.moveToNext()) records += TaskRecord(
                cursor.getString(0), cursor.getString(1), cursor.getInt(2),
                cursor.getInt(3) == 1,
                if (cursor.isNull(4)) null else cursor.getString(4),
                if (cursor.isNull(5)) null else cursor.getString(5),
                cursor.getString(6)
            )
        }
        return records
    }

    fun listProjects(): List<ProjectRecord> {
        val projects = mutableListOf<ProjectRecord>()
        readableDatabase.rawQuery("SELECT id,name FROM projects ORDER BY name", null).use { cursor ->
            while (cursor.moveToNext()) projects += ProjectRecord(cursor.getString(0), cursor.getString(1))
        }
        return projects
    }

    fun addProject(name: String): String {
        val normalized = TaskRules.projectName(name)
        val id = UUID.randomUUID().toString()
        val record = ContentValues().apply { put("id", id); put("name", normalized) }
        writableDatabase.insertOrThrow("projects", null, record)
        return id
    }

    fun add(title: String, priority: Int, dueDate: String?, projectId: String?,
            description: String = "") {
        val normalized = TaskRules.title(title)
        val validatedPriority = TaskRules.priority(priority)
        val validatedDue = TaskRules.due(dueDate)
        val validatedDescription = TaskRules.description(description)
        val record = ContentValues().apply {
            put("id", UUID.randomUUID().toString())
            put("title", normalized)
            put("priority", validatedPriority)
            put("completed", 0)
            put("created_at", System.currentTimeMillis())
            put("due_date", validatedDue)
            put("project_id", projectId)
            put("description", validatedDescription)
        }
        writableDatabase.insertOrThrow("tasks", null, record)
    }

    /** One SQLite transaction creates a new open task; the source remains untouched. */
    fun duplicateTask(id: String): String {
        require(id.isNotBlank()) { "Task ID must not be blank" }
        val duplicateId = UUID.randomUUID().toString()
        val db = writableDatabase
        db.beginTransaction()
        try {
            db.execSQL(
                "INSERT INTO tasks " +
                    "(id,title,priority,completed,created_at,completed_at," +
                    "created_at_exact,completed_at_exact,due_date,project_id,description) " +
                    "SELECT ?,title,priority,0,?,NULL,NULL,NULL,due_date,project_id,description " +
                    "FROM tasks WHERE id=?",
                arrayOf(duplicateId, System.currentTimeMillis(), id)
            )
            val copied = android.database.DatabaseUtils.longForQuery(
                db, "SELECT changes()", null
            )
            require(copied == 1L) { "Task no longer exists" }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        return duplicateId
    }

    /** Edits are guarded by field validation; no schema replacement or row deletion. */
    fun update(id: String, title: String, priority: Int, dueDate: String?, projectId: String?,
               description: String? = null) {
        val normalized = TaskRules.title(title)
        val validatedPriority = TaskRules.priority(priority)
        val validatedDue = TaskRules.due(dueDate)
        val fields = ContentValues().apply {
            put("title", normalized)
            put("priority", validatedPriority)
            put("due_date", validatedDue)
            put("project_id", projectId)
            if (description != null) put("description", TaskRules.description(description))
        }
        val count = writableDatabase.update("tasks", fields, "id=?", arrayOf(id))
        require(count == 1) { "Task no longer exists" }
    }

    fun setCompleted(id: String, completed: Boolean) {
        val flag = if (completed) 1 else 0
        val update = ContentValues().apply {
            put("completed", flag)
            if (completed) put("completed_at", System.currentTimeMillis())
            else putNull("completed_at")
            // This local action now uses millisecond precision; stale imported
            // timestamp originals must never survive completion changes.
            putNull("completed_at_exact")
        }
        // A repeated toggle does not rewrite the original completion timestamp.
        writableDatabase.update("tasks", update, "id=? AND completed<>?",
                                arrayOf(id, flag.toString()))
    }

    /**
     * Atomic edit of 1–200 selected task IDs. Validation and all writes share
     * one SQLite transaction, including recoverable local Trash transfers.
     */
    fun bulkEdit(ids: List<String>, action: String, value: String? = null): Int {
        require(ids.size in 1..200 && ids.none { it.isBlank() } && ids.toSet().size == ids.size) {
            "Select 1–200 unique tasks"
        }
        require(action in listOf("complete", "reopen", "priority", "project", "trash")) {
            "Unsupported bulk action"
        }
        val priority = if (action == "priority") {
            require(value in listOf("1", "2", "3", "4")) { "Priority must be P1–P4" }
            value!!.toInt()
        } else {
            require(action == "project" || value == null) { "Unexpected bulk action value" }
            null
        }

        val db = writableDatabase
        db.beginTransaction()
        try {
            for (id in ids) {
                require(db.rawQuery("SELECT 1 FROM tasks WHERE id=?", arrayOf(id))
                    .use { it.moveToFirst() }) { "A selected task no longer exists" }
            }
            if (action == "project" && value != null) {
                require(db.rawQuery("SELECT 1 FROM projects WHERE id=?", arrayOf(value))
                    .use { it.moveToFirst() }) { "Selected project no longer exists" }
            }
            val whenMillis = System.currentTimeMillis()
            for (id in ids) {
                when (action) {
                    "complete", "reopen" -> {
                        val flag = if (action == "complete") 1 else 0
                        val fields = ContentValues().apply {
                            put("completed", flag)
                            if (flag == 1) put("completed_at", whenMillis)
                            else putNull("completed_at")
                            putNull("completed_at_exact")
                        }
                        // Idempotent: do not erase exact imported completion time.
                        db.update("tasks", fields, "id=? AND completed<>?",
                            arrayOf(id, flag.toString()))
                    }
                    "priority" -> db.update("tasks",
                        ContentValues().apply { put("priority", priority!!) }, "id=?", arrayOf(id))
                    "project" -> db.update("tasks",
                        ContentValues().apply { put("project_id", value) }, "id=?", arrayOf(id))
                    else -> {
                        db.execSQL(
                            "INSERT INTO deleted_tasks (" +
                                "id,title,priority,completed,created_at,completed_at," +
                                "created_at_exact,completed_at_exact,due_date,project_id,description,deleted_at) " +
                                "SELECT id,title,priority,completed,created_at,completed_at," +
                                "created_at_exact,completed_at_exact,due_date,project_id,description,? " +
                                "FROM tasks WHERE id=?",
                            arrayOf(whenMillis, id)
                        )
                        require(db.delete("tasks", "id=?", arrayOf(id)) == 1) {
                            "Task changed during bulk deletion"
                        }
                    }
                }
            }
            db.setTransactionSuccessful()
            return ids.size
        } finally {
            db.endTransaction()
        }
    }

    /** Explicit user-controlled, local document export; never uploads task data. */
    fun exportPortableBackup(): ByteArray = PortableBackup.encode(readableDatabase)

    /** Neither the preview nor the restore is permitted to replace existing rows. */
    fun isEmptyForRestore(): Boolean {
        val db = readableDatabase
        return android.database.DatabaseUtils.queryNumEntries(db, "tasks") == 0L &&
            android.database.DatabaseUtils.queryNumEntries(db, "projects") == 0L &&
            android.database.DatabaseUtils.queryNumEntries(db, "deleted_tasks") == 0L
    }

    /** All-or-nothing restore. Recheck emptiness inside the exclusive transaction. */
    fun restorePortableBackup(snapshot: RestoreSnapshot) {
        val db = writableDatabase
        db.beginTransaction()
        try {
            require(android.database.DatabaseUtils.queryNumEntries(db, "tasks") == 0L &&
                android.database.DatabaseUtils.queryNumEntries(db, "projects") == 0L &&
                android.database.DatabaseUtils.queryNumEntries(db, "deleted_tasks") == 0L) {
                "Restore requires an empty Tasks database, including Trash."
            }
            for (project in snapshot.projects) {
                val values = ContentValues().apply {
                    put("id", project.id)
                    put("name", project.name)
                }
                db.insertOrThrow("projects", null, values)
            }
            for (task in snapshot.tasks) {
                val values = ContentValues().apply {
                    put("id", task.id)
                    put("title", task.title)
                    put("description", TaskRules.description(task.description))
                    put("priority", task.priority)
                    put("completed", if (task.completed) 1 else 0)
                    put("due_date", task.dueDate)
                    put("project_id", task.projectId)
                    put("created_at", task.createdAt)
                    put("created_at_exact", task.createdAtExact)
                    if (task.completedAt == null) putNull("completed_at")
                    else put("completed_at", task.completedAt)
                    put("completed_at_exact", task.completedAtExact)
                }
                db.insertOrThrow("tasks", null, values)
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    /** Move a complete row to local Trash atomically; never overwrite an ID. */
    fun delete(id: String): Boolean {
        val db = writableDatabase
        db.beginTransaction()
        try {
            if (!db.rawQuery("SELECT 1 FROM tasks WHERE id=?", arrayOf(id))
                    .use { it.moveToFirst() }) {
                db.setTransactionSuccessful()
                return false
            }
            db.execSQL(
                "INSERT INTO deleted_tasks (" +
                    "id,title,priority,completed,created_at,completed_at," +
                    "created_at_exact,completed_at_exact,due_date,project_id,description,deleted_at) " +
                    "SELECT id,title,priority,completed,created_at,completed_at," +
                    "created_at_exact,completed_at_exact,due_date,project_id,description,? " +
                    "FROM tasks WHERE id=?",
                arrayOf(System.currentTimeMillis(), id)
            )
            require(db.delete("tasks", "id=?", arrayOf(id)) == 1) {
                "Task changed during deletion"
            }
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }

    /** Restore task fields and exact timestamps with no project reassignment. */
    fun restoreDeletedTask(id: String): Boolean {
        val db = writableDatabase
        db.beginTransaction()
        try {
            val projectId = db.rawQuery(
                "SELECT project_id FROM deleted_tasks WHERE id=?", arrayOf(id)
            ).use { cursor ->
                if (!cursor.moveToFirst()) {
                    db.setTransactionSuccessful()
                    return false
                }
                if (cursor.isNull(0)) null else cursor.getString(0)
            }
            require(projectId == null || db.rawQuery(
                "SELECT 1 FROM projects WHERE id=?", arrayOf(projectId)
            ).use { it.moveToFirst() }) {
                "Original project no longer exists; task stays in Trash"
            }
            // PRIMARY KEY collisions roll back without removing Trash.
            db.execSQL(
                "INSERT INTO tasks (" +
                    "id,title,priority,completed,created_at,completed_at," +
                    "created_at_exact,completed_at_exact,due_date,project_id,description) " +
                    "SELECT id,title,priority,completed,created_at,completed_at," +
                    "created_at_exact,completed_at_exact,due_date,project_id,description " +
                    "FROM deleted_tasks WHERE id=?",
                arrayOf(id)
            )
            require(db.delete("deleted_tasks", "id=?", arrayOf(id)) == 1) {
                "Trash changed during restoration"
            }
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }
}
