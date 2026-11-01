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
    val projectId: String?
)

internal data class ProjectRecord(val id: String, val name: String)

/**
 * On-device private SQLite database. No Internet permission or server sync.
 *
 * V2 adds projects/dates, V3 completion timestamps, V4 exact imported timestamps.
 * All upgrades preserve existing task rows.
 */
internal class TasksDatabase(context: Context) :
    SQLiteOpenHelper(context, "goreecloud-tasks.db", null, 4) {

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
                "due_date TEXT, project_id TEXT REFERENCES projects(id) ON DELETE SET NULL)"
        )
        db.execSQL("CREATE INDEX idx_tasks_priority ON tasks(completed, priority, created_at)")
        db.execSQL("CREATE INDEX idx_tasks_due_date ON tasks(completed, due_date)")
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
    }

    fun listTasks(): List<TaskRecord> {
        val records = mutableListOf<TaskRecord>()
        readableDatabase.rawQuery(
            "SELECT id,title,priority,completed,due_date,project_id FROM tasks " +
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
                    if (cursor.isNull(5)) null else cursor.getString(5)
                )
            }
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

    fun add(title: String, priority: Int, dueDate: String?, projectId: String?) {
        val normalized = TaskRules.title(title)
        val validatedPriority = TaskRules.priority(priority)
        val validatedDue = TaskRules.due(dueDate)
        val record = ContentValues().apply {
            put("id", UUID.randomUUID().toString())
            put("title", normalized)
            put("priority", validatedPriority)
            put("completed", 0)
            put("created_at", System.currentTimeMillis())
            put("due_date", validatedDue)
            put("project_id", projectId)
        }
        writableDatabase.insertOrThrow("tasks", null, record)
    }

    /** Edits are guarded by field validation; no schema replacement or row deletion. */
    fun update(id: String, title: String, priority: Int, dueDate: String?, projectId: String?) {
        val normalized = TaskRules.title(title)
        val validatedPriority = TaskRules.priority(priority)
        val validatedDue = TaskRules.due(dueDate)
        val fields = ContentValues().apply {
            put("title", normalized)
            put("priority", validatedPriority)
            put("due_date", validatedDue)
            put("project_id", projectId)
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

    /** Explicit user-controlled, local document export; never uploads task data. */
    fun exportPortableBackup(): ByteArray = PortableBackup.encode(readableDatabase)

    /** Neither the preview nor the restore is permitted to replace existing rows. */
    fun isEmptyForRestore(): Boolean {
        val db = readableDatabase
        return android.database.DatabaseUtils.queryNumEntries(db, "tasks") == 0L &&
            android.database.DatabaseUtils.queryNumEntries(db, "projects") == 0L
    }

    /** All-or-nothing restore. Recheck emptiness inside the exclusive transaction. */
    fun restorePortableBackup(snapshot: RestoreSnapshot) {
        val db = writableDatabase
        db.beginTransaction()
        try {
            require(android.database.DatabaseUtils.queryNumEntries(db, "tasks") == 0L &&
                android.database.DatabaseUtils.queryNumEntries(db, "projects") == 0L) {
                "Restore requires an empty Tasks database. Export current tasks first."
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

    fun delete(id: String) {
        writableDatabase.delete("tasks", "id=?", arrayOf(id))
    }
}
