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
 * Version 2 adds project and due-date fields non-destructively; v1 tasks survive upgrade.
 */
internal class TasksDatabase(context: Context) :
    SQLiteOpenHelper(context, "goreecloud-tasks.db", null, 2) {

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
                "completed INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, " +
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
        val normalized = name.trim()
        require(normalized.isNotEmpty() && normalized.length <= 100) {
            "Project name must be 1–100 characters"
        }
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
        val update = ContentValues().apply { put("completed", if (completed) 1 else 0) }
        writableDatabase.update("tasks", update, "id=?", arrayOf(id))
    }

    fun delete(id: String) {
        writableDatabase.delete("tasks", "id=?", arrayOf(id))
    }
}
